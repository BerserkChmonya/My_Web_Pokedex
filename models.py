from typing import List, Optional

from sqlmodel import SQLModel, Field
from sqladmin import ModelView


class Pokemon(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    pokedex_number: int
    classification: str
    type1: str
    type2: str


class PokemonAdmin(ModelView, model=Pokemon):
    page_size = 20
    icon = "fa-solid fa-spaghetti-monster-flying"
    column_searchable_list = [Pokemon.name]
    column_sortable_list = [Pokemon.name, Pokemon.classification, Pokemon.type1, Pokemon.type2]
    if Pokemon.id is None:
        Pokemon.id = Pokemon.pokedex_number

    column_list = [
        Pokemon.pokedex_number,
        Pokemon.name,
        Pokemon.classification,
        Pokemon.type1,
        Pokemon.type2
    ]


class Trainer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    password_hash: str
    pokemons: str = ""
