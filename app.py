from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
CORS(app)

# MongoDB
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
mongo = PyMongo(app)
db = mongo.cx["circlEatsDB"]
users = db["users"]
donations = db["donor"]

# SIGNUP
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()
    if users.find_one({"email": data["email"]}):
        return jsonify({"error": "User already exists"}), 400

    hashed = generate_password_hash(data["password"])
    users.insert_one({
        "name": data["name"],
        "email": data["email"],
        "password": hashed
    })
    return jsonify({"message": "Signup successful!"}), 201

# LOGIN
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    user = users.find_one({"email": data["email"]})

    if user and check_password_hash(user["password"], data["password"]):
        return jsonify({
            "message": "Login successful",
            "user_id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"]
        }), 200

    return jsonify({"error": "Invalid credentials"}), 401

# CREATE DONATION  (Donor)
@app.route("/api/create_donation", methods=["POST"])
def create_donation():
    data = request.get_json()
    donations.insert_one({
        "user_id": data.get("user_id"),
        "item": data.get("item"),
        "quantity": data.get("quantity"),
        "location": data.get("location"),
        "status": "Pending",
        "requested_by": None,
        "accepted_by": None,
        "shelter_request": None,
        "notifications": []
    })
    return jsonify({"message": "Donation created"}), 201

# DONOR DASHBOARD — Clean, private
@app.route("/api/my_donations/<user_id>", methods=["GET"])
def my_donations(user_id):
    res = list(donations.find({"user_id": user_id}))
    for r in res:
        r["_id"] = str(r["_id"])
    return jsonify(res), 200

# ➡ Hides all volunteer notifications from others
@app.route("/api/my_notifications/<user_id>", methods=["GET"])
def my_notifications(user_id):
    res = []
    for d in donations.find({"user_id": user_id}):
        res.extend(d.get("notifications", []))
    return jsonify(res), 200

# SHELTER REQUESTS DELIVERY
@app.route("/api/shelter_request/<donation_id>", methods=["PUT"])
def shelter_request(donation_id):
    data = request.get_json()
    donations.update_one(
        {"_id": ObjectId(donation_id)},
        {"$set": {
            "status": "Requested",
            "requested_by": data.get("shelter"),  # 🔥 PRIVATE ownership
            "shelter_request": {
                "email": data.get("shelter"),
                "location": data.get("location"),
                "self_pickup": data.get("self_pickup", False)
            }
        }}
    )
    return jsonify({"message": "Request submitted"}), 200

# SHELTER DASHBOARD — Own private requests only
@app.route("/api/my_requests/<email>", methods=["GET"])
def my_requests(email):
    res = list(donations.find({"requested_by": email}))
    for r in res:
        r["_id"] = str(r["_id"])
    return jsonify(res), 200

# VOLUNTEER VISIBLE REQUESTS ONLY
@app.route("/api/shelter_requests", methods=["GET"])
def shelter_requests():
    res = list(donations.find({"status": "Requested"}))
    for r in res:
        r["_id"] = str(r["_id"])
    return jsonify(res), 200

# VOLUNTEER ACCEPT DELIVERY
@app.route("/api/accept_delivery/<donation_id>", methods=["PUT"])
def accept_delivery(donation_id):
    data = request.get_json()
    volunteer = data.get("volunteer")

    donations.update_one(
        {"_id": ObjectId(donation_id)},
        {"$set": {
            "status": "In Transit",
            "collected_by": volunteer,
            "accepted_by": volunteer  # 🔥 PRIVATE ownership
        }}
    )
    return jsonify({"message": "Delivery accepted"}), 200

# VOLUNTEER DASHBOARD — ONLY their accepted deliveries
@app.route("/api/my_deliveries/<email>", methods=["GET"])
def my_deliveries(email):
    res = list(donations.find({"accepted_by": email}))
    for r in res:
        r["_id"] = str(r["_id"])
    return jsonify(res), 200

# HEALTH CHECK
@app.route("/")
def home():
    return jsonify({"message": "CirclEats backend running!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
