from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Nombres fijos para índices y restricciones: así Alembic genera los mismos
# nombres en todas las máquinas y las migraciones pueden borrarlos por nombre.
CONVENCION_NOMBRES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCION_NOMBRES)
