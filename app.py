import streamlit as st
import requests
import base64
import json
import os
import pandas as pd

# Load API Keys from Streamlit Secrets
ID_ANALYZER_API_KEY = st.secrets["API"]["ID_ANALYZER_API_KEY"]
PROFILE_ID = "df915e0025b04d64b5af9d525eb0050d"  # Profile ID for ID Analyzer
API_URL = "https://api2.idanalyzer.com/scan"

# Function to fetch VIN details
def verify_vin(vin):
    """Fetch VIN details from NHTSA API"""
    api_url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json"
    response = requests.get(api_url)

    if response.status_code == 200:
        data = response.json().get("Results", [])
        vehicle_info = {
            "Make": next((item["Value"] for item in data if item["Variable"] == "Make"), "N/A"),
            "Model": next((item["Value"] for item in data if item["Variable"] == "Model"), "N/A"),
            "Model Year": next((item["Value"] for item in data if item["Variable"] == "Model Year"), "N/A"),
            "Trim": next((item["Value"] for item in data if item["Variable"] == "Trim"), "N/A"),
            "Body Class": next((item["Value"] for item in data if item["Variable"] == "Body Class"), "N/A"),
            "Fuel Type": next((item["Value"] for item in data if item["Variable"] == "Fuel Type - Primary"), "N/A"),
            "Vehicle Type": next((item["Value"] for item in data if item["Variable"] == "Vehicle Type"), "N/A"),
        }
        return vehicle_info
    return None

# Function to encode image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# Function to verify driver's license
def verify_license(image_path):
    try:
        document_base64 = encode_image(image_path)
        payload = {"profile": PROFILE_ID, "document": document_base64}
        headers = {"X-API-KEY": ID_ANALYZER_API_KEY, "Accept": "application/json", "Content-Type": "application/json"}
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API Error: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"error": str(e)}

# Streamlit UI
st.title("🚗 Auto VIN & Driver's License Verification 🆔")
st.write("Enter the VIN number or upload a driver's license to verify details.")

# Input for VIN Number
vin_number = st.text_input("Enter VIN Number:")

# Upload Driver's License Image
uploaded_file = st.file_uploader("Upload Driver's License (JPG/PNG)", type=["jpg", "png"])

if st.button("Verify Details"):
    if not vin_number and not uploaded_file:
        st.error("Please enter a VIN number or upload a Driver's License.")

    # Process VIN Verification
    if vin_number:
        st.subheader("🔍 VIN Details:")
        vin_details = verify_vin(vin_number)
        if vin_details:
            vin_df = pd.DataFrame(vin_details.items(), columns=["Attribute", "Value"])
            st.table(vin_df)
        else:
            st.error("❌ Invalid VIN number or no details found.")

    # Process Driver's License Verification
    if uploaded_file:
        st.subheader("🆔 Driver's License Verification:")
        file_path = f"temp_{uploaded_file.name}"
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())

        license_data = verify_license(file_path)

        if "error" in license_data:
            st.error(license_data["error"])
        else:
            # Extract relevant details
            full_name = license_data["data"].get("fullName", [{"value": "N/A"}])[0]["value"]
            license_number = license_data["data"].get("documentNumber", [{"value": "N/A"}])[0]["value"]
            dob = license_data["data"].get("dob", [{"value": "N/A"}])[0]["value"]
            expiry = license_data["data"].get("expiry", [{"value": "N/A"}])[0]["value"]
            address = license_data["data"].get("address1", [{"value": "N/A"}])[0]["value"]
            decision = license_data.get("decision", "Unknown")

            # Show license details in table format
            license_df = pd.DataFrame([
                ["Full Name", full_name],
                ["License Number", license_number],
                ["Date of Birth", dob],
                ["Expiry Date", expiry],
                ["Address", address],
                ["Verification Status", decision.capitalize()],
            ], columns=["Attribute", "Value"])
            st.table(license_df)

            # Warnings section
            if "warning" in license_data:
                warnings_data = [{"Description": w["description"], "Confidence": w["confidence"], "Decision": w["decision"]} for w in license_data["warning"]]
                warnings_df = pd.DataFrame(warnings_data)
                st.warning("⚠️ Warnings:")
                st.table(warnings_df)

            # Decision Output
            if decision == "reject":
                st.error("❌ License verification was REJECTED.")
            elif decision == "review":
                st.warning("🔍 License requires MANUAL REVIEW.")
            else:
                st.success("✅ License Verification PASSED!")

    # Cleanup uploaded file
    if os.path.exists(file_path):
        os.remove(file_path)
