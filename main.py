from fastapi import FastAPI, Request

from models.Userlogin import UserRegister

from controllers.o365 import login_o365 , auth_callback_o365
from controllers.google import login_google , auth_callback_google
from controllers.firebase import register_user_firebase, login_user_firebase


app = FastAPI()

@app.get("/")
async def hello():
    return {
        "Hello": "World"
        , "date": "2024-07-17"
    }

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
async def login_custom(user: UserRegister):
    return await login_user_firebase(user)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)