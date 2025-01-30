import streamlit as st
import requests
import base64
import json
import os

# Configuration
API_KEY = "Zz2yjmXLdKrebG74iYh4HqbsQVl2lRcJ"  # Replace with your IDAnalyzer API Key
PROFILE_ID = "995c339381194eeda07037022310b30f"  # Profile ID for verification
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
        headers = {"X-API-KEY": API_KEY, "Accept": "application/json", "Content-Type": "application/json"}
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API Error: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"error": str(e)}

# Streamlit UI
st.title("🚗 Auto VIN & Driver's License Verification 🆔")

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
            st.json(vin_details)
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
            st.json(license_data)
            
            if "warning" in license_data:
                st.warning("⚠️ Warnings:")
                for warning in license_data["warning"]:
                    st.write(f"🔸 {warning['description']} (Confidence: {warning['confidence']}, Decision: {warning['decision']})")
            
            if license_data.get("decision") == "reject":
                st.error("❌ License verification was REJECTED.")
            elif license_data.get("decision") == "review":
                st.warning("🔍 License requires MANUAL REVIEW.")
            else:
                st.success("✅ License Verification PASSED!")
    
    # Cleanup uploaded file
    if os.path.exists(file_path):
        os.remove(file_path)
