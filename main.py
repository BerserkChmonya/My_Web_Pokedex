import sqlite3
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker
from sqlmodel import create_engine, select, Session
from sqladmin import Admin
from models import PokemonAdmin, Pokemon, Trainer
from fastapi import HTTPException, status

from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from typing import Optional

path = Path(__file__).parent

DB_URL = "sqlite:///pokedex.sqlite"
TRAINERS_DB_URL = "sqlite:///trainers.sqlite"

app = FastAPI(title="Pokédex")
app.mount("/static", StaticFiles(directory=path / "static"), name="static")
templates = Jinja2Templates(directory=path / "templates")

# db engine
engine = create_engine(DB_URL)
trainers_engine = create_engine(TRAINERS_DB_URL)
admin = Admin(app, engine)
admin.add_view(PokemonAdmin)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
TrainersSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=trainers_engine)


def get_pokedex_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_trainers_db():
    db = TrainersSessionLocal()
    try:
        yield db
    finally:
        db.close()


def token_admin_auth():
    username = get_username_from_token()
    return username == "admin"


def get_username_from_token():
    user_info = decode_token(TOKEN.get("access_token"))
    if user_info is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username = user_info.get("sub")
    return username


@app.get("/", response_class=HTMLResponse)
def hello(request: Request):
    context = {
        'request': request,
        'title': 'My Pokedex'
    }
    return templates.TemplateResponse('home.tpl.html', context)


@app.get("/api/pokemons")
def get_pokemons(db: Session = Depends(get_pokedex_db)):
    if not token_admin_auth():
        raise HTTPException(401, detail="Unauthorized")
    # SELECT * FROM pokemon LIMIT 50;
    statement = select(Pokemon)
    results = db.exec(statement).all()
    return results


@app.get("/api/pokemons/{pokedex_number}")
def get_pokemon(pokedex_number: int, db: Session = Depends(get_pokedex_db)):
    if not token_admin_auth():
        raise HTTPException(401, detail="Unauthorized")
    # SELECT * FROM pokemon WHERE pokedex_number=pokedex_number\
    statement = select(Pokemon).where(Pokemon.pokedex_number == pokedex_number)
    result = db.exec(statement).one_or_none()

    if result is None:
        raise HTTPException(status_code=404, detail='Pokemon not found')
    return result


@app.get('/pokedex', response_class=HTMLResponse)
def view_list_of_pokemons(request: Request, db: Session = Depends(get_pokedex_db)):
    statement = select(Pokemon).limit(50)
    pokemons = db.execute(statement).scalars().all()

    context = {
        'request': request,
        'title': 'Všetci Pokémoni na jednom mieste | Pokédex',
        'pokemons': pokemons
    }

    return templates.TemplateResponse('pokemon-list.tpl.html', context)


@app.get("/pokedex/{pokedex_number}", response_class=HTMLResponse)
def view_detail_of_pokemon(request: Request, pokedex_number: int, db: Session = Depends(get_pokedex_db)):
    statement = select(Pokemon).where(Pokemon.pokedex_number == pokedex_number)
    pokemon = db.execute(statement).scalars().one_or_none()
    if pokemon is None:
        context = {
            "request": request,
            "title": "Pokémon sa nenašiel | Pokédex"
        }
        return templates.TemplateResponse("404.tpl.html", context)

    context = {
        "request": request,
        "title": f"{pokemon.name} | Pokédex",
        "pokemon": pokemon,
    }

    return templates.TemplateResponse("pokemon-detail.tpl.html", context)


@app.get("/api/create", response_class=HTMLResponse)
async def create_pokemon(request: Request):
    if not token_admin_auth():
        raise HTTPException(401, detail="Unauthorized")
    context = {
        "request": request,
        "title": "Creating Pokémon",
    }
    return templates.TemplateResponse("create.html", context)


@app.post("/api/create")
async def create_pokemon(request: Request, db: Session = Depends(get_pokedex_db)):
    if not token_admin_auth():
        raise HTTPException(401, detail="Unauthorized")
    form_data = await request.form()
    pokemon_data = {
        "id": form_data.get("pokedex_number"),
        "name": form_data.get("name"),
        "pokedex_number": int(form_data.get("pokedex_number")),
        "classification": form_data.get("classification"),
        "type1": form_data.get("type1"),
        "type2": form_data.get("type2") or None
    }

    existing_pokemon = db.execute(
        select(Pokemon).where(Pokemon.pokedex_number == form_data.get("pokedex_number"))).first()
    if existing_pokemon:
        raise HTTPException(status_code=400, detail="A Pokemon with this Pokedex number already exists")
    new_pokemon = Pokemon(**pokemon_data)
    db.add(new_pokemon)
    db.commit()
    db.refresh(new_pokemon)
    return new_pokemon


# ---------------------- trainer account
# Secret key to sign JWT tokens
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
TOKEN = {}


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Security helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


# Token related helper functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        # Token has expired
        return None


@app.get("/api/trainers", response_class=HTMLResponse)
async def get_trainers(request: Request):
    context = {
        "request": request,
        "title": "Trainers",
    }
    return templates.TemplateResponse("trainers.html", context)


# Registration endpoint
@app.post("/api/register")
async def register_trainer(request: Request, db: Session = Depends(get_trainers_db)):
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")

    # Hash the password
    hashed_password = get_password_hash(password)

    result = db.execute(select(func.max(Trainer.id))).scalar_one()
    last_trainer_id = result if result is not None else 0
    id = last_trainer_id + 1 if last_trainer_id else 1
    # Check if the username already exists
    existing_trainer = db.execute(select(Trainer).filter_by(username=username)).scalars().first()
    if existing_trainer:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Create a new trainer
    new_trainer = Trainer(id=id, username=username, password_hash=hashed_password)
    db.add(new_trainer)
    db.commit()
    db.refresh(new_trainer)

    return new_trainer


# Login endpoint
@app.post("/api/login")
async def login_trainer(request: Request, db: Session = Depends(get_trainers_db)):
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")

    # Retrieve the trainer from the database
    trainer = db.execute(select(Trainer).where(Trainer.username == username)).scalars().first()
    # Check if the trainer exists and if the password is correct
    if not trainer:
        print("no trainer")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Username not found")
    elif not verify_password(password, trainer.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")

    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(data={"sub": trainer.username}, expires_delta=access_token_expires)
    global TOKEN
    TOKEN = {"access_token": access_token, "token_type": "bearer"}
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/profile",response_class=HTMLResponse)
async def get_profile(request: Request):
    # Fetch user profile from database
    username = get_username_from_token()
    with Session(trainers_engine) as session:
        trainer = session.query(Trainer).filter(Trainer.username == username).first()
        if trainer is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return templates.TemplateResponse("profile.tpl.html", {"request": request, "trainer": trainer, "pokemon_list": get_pokemon_list()})


def get_pokemon_list():
    # Connect to the SQLite database
    conn = sqlite3.connect('pokedex.sqlite')
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM pokemon")

    pokemon_list = cursor.fetchall()

    cursor.close()
    conn.close()

    return pokemon_list


@app.post("/api/add_pokemon/{pokemon_id}")
def add_pokemon(pokemon_id: int):
    if TOKEN is None or "access_token" not in TOKEN:
        return HTTPException(status_code=401, detail="Unauthorized")
    user_info = decode_token(TOKEN.get("access_token"))
    if user_info is None:
        return HTTPException(status_code=401, detail="Unauthorized")
    username = user_info.get("sub")

    with Session(trainers_engine) as session:
        trainer = session.query(Trainer).filter(Trainer.username == username).first()

        if trainer is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if f"{pokemon_id}" in trainer.pokemons:
            raise HTTPException(status_code=404, detail="Pokemon already exists")

        trainer.pokemons += f",{pokemon_id}" if trainer.pokemons != "" else f"{pokemon_id}"

        session.commit()
        return {"message": f"Pokemon with ID {pokemon_id} added to trainer {username}'s pokemons"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        port=80,       # port, na ktorom sa aplikácia spustí, default=8000
        host="0.0.0.0",  # bude akceptovať komunikáciu z akejkoľvek IP adresy, default=127.0.0.1
        reload=True,     # v prípade zmeny súboru sa aplikácia automaticky reštartne, default=False
    )
