from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent.parent/ "data"



PORTFOLIOS_DATA= "portfolios.json"


USERS_DATA = "users.json"
#Столбцы в таблице users_date
USER_ID = "user_id"
USER_NAME = "username"
HASHED_PASSWORD ="hashed_password"
SALT = "salt"
REGISTRATION_DATE = "registration_date"