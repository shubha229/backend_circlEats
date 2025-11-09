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

# ✅ Use your actual database circlEatsDB
app.config["MONGO_URI"] = os.getenv("MONGO_URI")  # e.g. mongodb+srv://.../circlEatsDB
mongo = PyMongo(app)

# ✅ Collections
users = mongo.db.users
donations = mongo.db.donor  # your chosen collection name

# -------------------------------
# 1️⃣ Signup
# -------------------------------
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()
    if users.find_one({"email": data["email"]}):
        return jsonify({"error": "User already exists"}), 400
    hashed_pw = generate_password_hash(data["password"])
    users.insert_one({
        "name": data["name"],
        "email": data["email"],
        "password": hashed_pw
    })
    return jsonify({"message": "Signup successful!"}), 201

# -------------------------------
# 2️⃣ Login
# -------------------------------
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

# -------------------------------
# 3️⃣ Create Donation
# -------------------------------
@app.route("/api/create_donation", methods=["POST"])
def create_donation():
    try:
        data = request.get_json()
        donations.insert_one({
            "user_id": data.get("user_id"),
            "item": data.get("item"),
            "quantity": data.get("quantity"),
            "location": data.get("location"),
            "status": "Pending",
            "collected_by": None,
            "donated_to": None
        })
        return jsonify({"message": "Donation created successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------
# 4️⃣ Get All Donations
# -------------------------------
@app.route("/api/donations", methods=["GET"])
def get_donations():
    result = []
    for d in donations.find():
        d["_id"] = str(d["_id"])
        result.append(d)
    return jsonify(result), 200

# ✅ Get donations by user_id
@app.route("/api/my_donations/<user_id>", methods=["GET"])
def get_user_donations(user_id):
    data = []
    for d in donations.find({"user_id": user_id}):
        d["_id"] = str(d["_id"])
        data.append(d)
    return jsonify(data), 200

# -------------------------------
# 5️⃣ Collect Donation (Volunteer)
# -------------------------------
@app.route("/api/collect_donation/<donation_id>", methods=["PUT"])
def collect_donation(donation_id):
    data = request.get_json()
    result = donations.update_one(
        {"_id": ObjectId(donation_id)},
        {"$set": {"status": "Collected", "collected_by": data.get("volunteer")}}
    )
    return jsonify({"message": "Donation collected!" if result.modified_count else "Donation not found"}), 200

# -------------------------------
# 6️⃣ Donate to Shelter
# -------------------------------
@app.route("/api/donate_to_shelter/<donation_id>", methods=["PUT"])
def donate_to_shelter(donation_id):
    data = request.get_json()
    result = donations.update_one(
        {"_id": ObjectId(donation_id)},
        {"$set": {"status": "Donated", "donated_to": data.get("shelter")}}
    )
    return jsonify({"message": "Donation marked as donated"}), 200

# -------------------------------
# 7️⃣ Health Check
# -------------------------------
@app.route("/")
def home():
    return jsonify({"message": "CirclEats backend running successfully!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
