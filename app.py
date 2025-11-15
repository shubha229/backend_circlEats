from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from dotenv import load_dotenv
import os
from geopy.geocoders import Nominatim

load_dotenv()

app = Flask(__name__)
CORS(app)

# ✅ Use your actual database circlEatsDB
app.config["MONGO_URI"] = os.getenv("MONGO_URI")  # e.g. mongodb+srv://.../circlEatsDB
mongo = PyMongo(app)

# ✅ Collections
client = mongo.cx
db = client["circlEatsDB"]
users = db["users"]
donations = db["donor"]

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

from geopy.geocoders import Nominatim

@app.route("/api/shelter_request/<donation_id>", methods=["PUT"])
def shelter_request(donation_id):
    data = request.get_json()
    shelter_email = data.get("shelter")
    location_data = data.get("location")  # e.g. "13.1486, 77.6035"

    # Convert coordinates -> human readable address
    geolocator = Nominatim(user_agent="circlEats")
    lat, lon = location_data.split(",")
    address = geolocator.reverse(f"{lat}, {lon}").address

    update_data = {
        "status": "Requested",
        "shelter_request": {
            "email": shelter_email,
            "location": address,     # ✅ Store full address instead of coordinates
            "self_pickup": data.get("self_pickup", False)
        }
    }

    result = donations.update_one(
        {"_id": ObjectId(donation_id)},
        {"$set": update_data}
    )

    if result.modified_count:
        return jsonify({"message": "Food request created successfully!"}), 200
    else:
        return jsonify({"error": "Donation not found"}), 404

# ✅ Shelter Accepts Food (includes location)
@app.route("/api/shelter_accept/<donation_id>", methods=["PUT"])
def shelter_accept(donation_id):
    try:
        data = request.get_json()
        shelter_email = data.get("shelter")
        shelter_location = data.get("location")

        if not shelter_email or not shelter_location:
            return jsonify({"error": "Shelter email and location required"}), 400

        result = donations.update_one(
            {"_id": ObjectId(donation_id)},
            {
                "$set": {
                    "status": "Donated",
                    "donated_to": shelter_email,
                    "shelter_location": shelter_location,
                }
            },
        )

        if result.modified_count:
            return jsonify({"message": "Donation successfully assigned to shelter"}), 200
        else:
            return jsonify({"error": "Donation not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/shelter_requests", methods=["GET"])
def get_shelter_requests():
    result = []
    for d in donations.find({
        "status": "Requested",
        "shelter_request.self_pickup": {"$ne": True}
    }):
        d["_id"] = str(d["_id"])
        result.append(d)
    return jsonify(result), 200

@app.route("/api/my_deliveries/<volunteer>", methods=["GET"])
def get_my_deliveries(volunteer):
    try:
        deliveries = list(donations.find({
            "collected_by": volunteer,      # volunteer email is stored here
            "status": "In Transit"          # accepted deliveries
        }))

        for d in deliveries:
            d["_id"] = str(d["_id"])
            if "shelter_request" in d and d["shelter_request"]:
                if "_id" in d["shelter_request"]:
                    d["shelter_request"]["_id"] = str(d["shelter_request"]["_id"])

        return jsonify(deliveries), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Server error"}), 500

    
@app.route("/api/accept_delivery/<donation_id>", methods=["PUT"])
def accept_delivery(donation_id):
    data = request.get_json()
    volunteer_email = data.get("volunteer")

    donation = donations.find_one({"_id": ObjectId(donation_id)})
    if not donation:
        return jsonify({"error": "Donation not found"}), 404

    donations.update_one(
        {"_id": ObjectId(donation_id)},
        {
            "$set": {
                "status": "In Transit",
                "collected_by": volunteer_email,
                "volunteer_request": {"email": volunteer_email}
            },
            "$push": {
                "notifications": {
                    "to": donation.get("shelter_request", {}).get("email"),
                    "message": f"Volunteer {volunteer_email} accepted your food delivery request.",
                }
            }
        }
    )

    return jsonify({"message": "Delivery accepted and shelter notified!"}), 200

@app.route("/api/my_shelter_requests/<email>", methods=["GET"])
def my_shelter_requests(email):
    data = []
    for d in donations.find({"shelter_request.email": email}):
        d["_id"] = str(d["_id"])
        data.append(d)
    return jsonify(data), 200


#---Shelter fetches notifications----    
@app.route("/api/notifications/<shelter_email>", methods=["GET"])
def get_notifications(shelter_email):
    notes = []
    for d in donations.find({"notifications.to": shelter_email}):
        for n in d.get("notifications", []):
            if n.get("to") == shelter_email:
                notes.append(n)
    return jsonify(notes), 200


# -------------------------------
# 7️⃣ Health Check
# -------------------------------
@app.route("/")
def home():
    return jsonify({"message": "CirclEats backend running successfully!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
