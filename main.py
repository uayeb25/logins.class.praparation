from fastapi import FastAPI, Request, Response

from models.UserRegister import UserRegister
from models.UserLogin import UserLogin
from models.UserActivation import UserActivation
from models.Card import Card

from controllers.o365 import login_o365 , auth_callback_o365
from controllers.google import login_google , auth_callback_google
from controllers.firebase import register_user_firebase, login_user_firebase, generate_activation_code, activate_user

from controllers.card import fetch_cards, fetch_card, delete_card, fetch_update_card, fetch_create_card


from fastapi.middleware.cors import CORSMiddleware


from utils.security import validate, validate_func, validate_for_inactive

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos
    allow_headers=["*"],  # Permitir todos los encabezados
)

@app.get("/")
async def hello():
    return {
        "Hello": "World"
        , "version": "0.1.18"
    }



@app.get("/cards")
async def cards(responce: Response):
    responce.headers["Cache-Control"] = "no-cache"
    return await fetch_cards()

@app.post("/cards")
async def cards(responce: Response, card: Card):
    responce.headers["Cache-Control"] = "no-cache"
    return await fetch_create_card( card.title, card.description )

@app.get("/cards/{id}")
async def cards(responce: Response, id: int):
    responce.headers["Cache-Control"] = "no-cache"
    return await fetch_card(id)

@app.delete("/cards/{id}")
async def cardDelete(responce: Response, id: int):
    responce.headers["Cache-Control"] = "no-cache"
    return await delete_card(id)

@app.put("/cards/{id}")
async def cardUpdate(responce: Response, id: int, card: Card):
    responce.headers["Cache-Control"] = "no-cache"
    return await fetch_update_card(id, card.title, card.description )




@app.get("/login")
async def login():
    return await login_o365()

@app.get("/auth/callback")
async def authcallback(request: Request):
    return await auth_callback_o365(request)

@app.get("/login/google")
async def logingoogle():
    return await login_google()

@app.get("/auth/google/callback")
async def authcallbackgoogle(request: Request):
    return await auth_callback_google(request)



@app.post("/register")
async def register(user: UserRegister):
    return await register_user_firebase(user)

@app.post("/login/custom")
async def login_custom(user: UserLogin):
    return await login_user_firebase(user)



@app.get("/user")
@validate
async def user(request: Request):
    return {
        "email": request.state.email
        , "firstname": request.state.firstname
        , "lastname": request.state.lastname
    }

@app.post("/user/{email}/code")
@validate_func
async def generate_code(request: Request, email: str):
    return await generate_activation_code(email)

@app.put("/user/code/{code}")
@validate_for_inactive
async def generate_code(request: Request, code: int):
    user = UserActivation(email=request.state.email, code=code)
    return await activate_user(user)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)