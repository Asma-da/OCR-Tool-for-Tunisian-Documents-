from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Form
from database import get_collection
from auth_utils import hash_password, verify_password, create_access_token, get_current_user
from schemas import LoginSchema, RegisterSchema

router = APIRouter()
templates = Jinja2Templates(directory="templates")

users_col = get_collection("users")
uploads_col = get_collection("uploads")


# ----------------
# Registration
# ----------------

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register", response_class=HTMLResponse)
async def register_page_post(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirmPassword: str = Form(...)
):
    # Password confirmation
    if password != confirmPassword:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Passwords do not match"}
        )

    # Email uniqueness
    if users_col.find_one({"email": email}):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "User already exists"}
        )

    # Username uniqueness
    if users_col.find_one({"username": username}):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Username already taken"}
        )

    # Hash password and save user
    hashed_pw = hash_password(password)
    users_col.insert_one({
        "username": username,
        "email": email,
        "password": hashed_pw,
        "role": "user"
    })

    # Success message
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "msg": "Registration successful. Please log in."}
    )
# ----------------
# Login
# ----------------

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

from fastapi import Form

@router.post("/login", response_class=HTMLResponse)
async def login_page_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    user = users_col.find_one({"email": email})

    if not user or not verify_password(password, user["password"]):
        # Instead of raising HTTPException, return the template with an error
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid email or password"
        })

    # Create token
    token = create_access_token({
        "user_id": str(user["_id"]),
        "username": user["username"],
        "role": user.get("role", "user")
    })

    # Determine redirect URL
    target_url = "/admin" if user.get("role") == "admin" else f"/{user['username']}/dashboard"

    # Set cookie and redirect
    redirect_response = RedirectResponse(url=target_url, status_code=303)
    redirect_response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        samesite="lax"
    )
    return redirect_response


# ----------------
# Admin dashboard
# ----------------

from datetime import datetime, timedelta
from collections import Counter

@router.get("/admin", response_class=HTMLResponse)
async def admin_home(request: Request, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        return RedirectResponse(url=f"/{current_user['username']}/dashboard")

    # ------------------- USERS -------------------
    users = list(users_col.find())
    for u in users:
        u["_id"] = str(u["_id"])

    # ------------------- UPLOADS -------------------
    uploads = list(uploads_col.find().sort("timestamp", -1))
    for u in uploads:
        u["_id"] = str(u["_id"])
        u["username"] = u.get("username") or "Unknown"
        u["filename"] = u.get("filename") or u.get("front_filename") or "N/A"
        u["timestamp"] = u.get("timestamp").strftime("%Y-%m-%d %H:%M") if u.get("timestamp") else "N/A"

    # ------------------- STATS -------------------
    total_users = len(users)
    total_docs = len(uploads)

    # ---------------- UPLOADS PER DAY ----------------
    today = datetime.utcnow()
    last_7_days = [(today - timedelta(days=i)).date() for i in range(6, -1, -1)]
    uploads_per_day_counts = [
        uploads_col.count_documents({
            "timestamp": {"$gte": datetime.combine(day, datetime.min.time()),
                          "$lt": datetime.combine(day, datetime.max.time())}
        }) for day in last_7_days
    ]
    uploads_per_day_data = {
        "labels": [day.strftime("%Y-%m-%d") for day in last_7_days],
        "values": uploads_per_day_counts
    }

    # ---------------- UPLOADS BY DOCUMENT TYPE ----------------
    doc_type_counter = Counter(d.get("doc_type", "Unknown") for d in uploads)
    uploads_by_type_data = {
        "labels": list(doc_type_counter.keys()),
        "values": list(doc_type_counter.values())
    }

    # ---------------- TOP USERS ----------------
    user_counter = Counter(d.get("username", "Unknown") for d in uploads)
    top_users_list = user_counter.most_common(5)
    top_users_data = {
        "labels": [u[0] for u in top_users_list],
        "values": [u[1] for u in top_users_list]
    }

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "username": current_user["username"],
        "users": users,
        "uploads": uploads,
        "total_users": total_users,
        "total_docs": total_docs,
        "uploads_per_day": uploads_per_day_data,
        "uploads_by_type": uploads_by_type_data,
        "top_users": top_users_data
    })

# ----------------
# User Dashboard
# ----------------

@router.get("/{username}/dashboard", response_class=HTMLResponse)
async def user_dashboard(
        username: str,
        request: Request,
        current_user: dict = Depends(get_current_user)
):
    # Ensure user can only access their own dashboard
    if current_user["username"] != username:
        raise HTTPException(status_code=403, detail="Access forbidden")

    # Get user's upload history
    user_uploads = list(uploads_col.find({"user_id": current_user["_id"]}))

    return templates.TemplateResponse("user_dashboard.html", {
        "request": request,
        "username": current_user["username"],
        "uploads": user_uploads
    })


# ----------------
# Logout
# ----------------

@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response