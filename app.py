from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
import os

app = Flask(__name__)
CORS(app)

# MongoDB Atlas Config
app.config["MONGO_URI"] = "mongodb+srv://circlEatsUser:yourpassword@cluster0.mongodb.net/circlEatsDB"
mongo = PyMongo(app)

# Collections
users = mongo.db.users
donations = mongo.db.donations

# -------------------------------
# 1️⃣ Signup Route
# -------------------------------
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if users.find_one({"email": email}):
        return jsonify({"error": "User already exists"}), 400

    hashed_pw = generate_password_hash(password)
    users.insert_one({"name": name, "email": email, "password": hashed_pw})
    return jsonify({"message": "Signup successful!"}), 201

# -------------------------------
# 2️⃣ Login Route
# -------------------------------
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = users.find_one({"email": email})
    if user and check_password_hash(user["password"], password):
        return jsonify({
            "message": "Login successful",
            "user_id": str(user["_id"]),
            "name": user["name"]
        }), 200
    return jsonify({"error": "Invalid credentials"}), 401

# -------------------------------
# 3️⃣ Create Donation
# -------------------------------
@app.route("/api/create_donation", methods=["POST"])
def create_donation():
    data = request.get_json()
    user_id = data.get("user_id")
    item = data.get("item")
    quantity = data.get("quantity")
    location = data.get("location")

    donations.insert_one({
        "user_id": ObjectId(user_id),
        "item": item,
        "quantity": quantity,
        "location": location,
        "status": "Pending",
        "collected_by": None,
        "donated_to": None
    })
    return jsonify({"message": "Donation created successfully"}), 201

# -------------------------------
# 4️⃣ Mark as Collected
# -------------------------------
@app.route("/api/collect_donation/<donation_id>", methods=["PUT"])
def collect_donation(donation_id):
    data = request.get_json()
    volunteer = data.get("volunteer")

    result = donations.update_one(
        {"_id": ObjectId(donation_id)},
        {"$set": {"status": "Collected", "collected_by": volunteer}}
    )
    if result.modified_count:
        return jsonify({"message": "Donation marked as collected"}), 200
    return jsonify({"error": "Donation not found"}), 404

# -------------------------------
# 5️⃣ Mark as Donated
# -------------------------------
@app.route("/api/donate_to_shelter/<donation_id>", methods=["PUT"])
def donate_to_shelter(donation_id):
    data = request.get_json()
    shelter = data.get("shelter")

    result = donations.update_one(
        {"_id": ObjectId(donation_id)},
        {"$set": {"status": "Donated", "donated_to": shelter}}
    )
    if result.modified_count:
        return jsonify({"message": "Donation marked as donated"}), 200
    return jsonify({"error": "Donation not found"}), 404

# -------------------------------
# 6️⃣ Get All Donations (for Admin/Volunteer view)
# -------------------------------
@app.route("/api/donations", methods=["GET"])
def get_donations():
    all_donations = []
    for d in donations.find():
        d["_id"] = str(d["_id"])
        d["user_id"] = str(d["user_id"])
        all_donations.append(d)
    return jsonify(all_donations), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
