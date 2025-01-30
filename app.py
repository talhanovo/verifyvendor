import streamlit as st
import requests
import base64
import json
import os
import pandas as pd

# Load API Keys from Streamlit Secrets
ID_ANALYZER_API_KEY = st.secrets["API"]["ID_ANALYZER_API_KEY"]
PROFILE_ID = "5b40b8dae4784cd2b0cddd87b06d926f"  # Profile ID for ID Analyzer
API_URL = "https://api2.idanalyzer.com/scan"

# Initialize session state for dynamic fields
if "vin_list" not in st.session_state:
    st.session_state.vin_list = [""]
if "license_list" not in st.session_state:
    st.session_state.license_list = [None]

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
def encode_image(image):
    return base64.b64encode(image.read()).decode("utf-8")

# Function to verify driver's license
def verify_license(image_data):
    try:
        payload = {"profile": PROFILE_ID, "document": image_data}
        headers = {"X-API-KEY": ID_ANALYZER_API_KEY, "Accept": "application/json", "Content-Type": "application/json"}
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API Error: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"error": str(e)}

# Streamlit UI
st.title("🚗 Vendor Verification form")
st.write("Enter **one or more VIN numbers** and upload **one or more driver's licenses** to verify details.")

# Section for VIN numbers
st.subheader("🔍 Enter VIN Numbers of your Fleet")

# Display VIN input fields dynamically
for i, vin in enumerate(st.session_state.vin_list):
    col1, col2 = st.columns([0.8, 0.2])
    st.session_state.vin_list[i] = col1.text_input(f"VIN {i+1}:", value=vin, key=f"vin_{i}")
    if col2.button("❌", key=f"remove_vin_{i}") and len(st.session_state.vin_list) > 1:
        st.session_state.vin_list.pop(i)
        st.experimental_rerun()

# Add VIN Button (Disabled if last VIN field is empty)
st.button("➕ Add VIN", disabled=not st.session_state.vin_list[-1], key="add_vin", on_click=lambda: st.session_state.vin_list.append(""))

# Section for Driver’s License Upload
st.subheader("🆔 Upload Driver’s Licenses")

# Display license upload fields dynamically
for i, license_file in enumerate(st.session_state.license_list):
    col1, col2 = st.columns([0.8, 0.2])
    st.session_state.license_list[i] = col1.file_uploader(f"License {i+1}:", type=["jpg", "png"], key=f"license_{i}")
    if col2.button("❌", key=f"remove_license_{i}") and len(st.session_state.license_list) > 1:
        st.session_state.license_list.pop(i)
        st.experimental_rerun()

# Add License Button (Disabled if last license field is empty)
st.button("➕ Add License", disabled=not st.session_state.license_list[-1], key="add_license", on_click=lambda: st.session_state.license_list.append(None))

# Verify Button
if st.button("Submit"):
    if not any(st.session_state.vin_list) and not any(st.session_state.license_list):
        st.error("⚠️ Please enter **at least one VIN number** or **upload at least one driver's license**.")
    
    # Process VIN Verification
    if any(st.session_state.vin_list):
        st.subheader("🚘 VIN Verification Results")
        vin_results = []
        for vin in st.session_state.vin_list:
            if vin:
                vin_details = verify_vin(vin)
                if vin_details:
                    vin_results.append([vin] + list(vin_details.values()))
                else:
                    vin_results.append([vin, "❌ Invalid VIN"])
        
        vin_df = pd.DataFrame(vin_results, columns=["VIN", "Make", "Model", "Model Year", "Trim", "Body Class", "Fuel Type", "Vehicle Type"])
        st.table(vin_df)

    # Process Driver’s License Verification
    if any(st.session_state.license_list):
        st.subheader("🆔 Driver’s License Verification Results")
        license_results = []
        warnings_results = []

        for license_file in st.session_state.license_list:
            if license_file:
                image_data = encode_image(license_file)
                license_data = verify_license(image_data)

                if "error" in license_data:
                    st.error(license_data["error"])
                    continue

                # Extract relevant details
                full_name = license_data["data"].get("fullName", [{"value": "N/A"}])[0]["value"]
                license_number = license_data["data"].get("documentNumber", [{"value": "N/A"}])[0]["value"]
                dob = license_data["data"].get("dob", [{"value": "N/A"}])[0]["value"]
                expiry = license_data["data"].get("expiry", [{"value": "N/A"}])[0]["value"]
                address = license_data["data"].get("address1", [{"value": "N/A"}])[0]["value"]
                decision = license_data.get("decision", "Unknown")

                # Store results in table
                license_results.append([full_name, license_number, dob, expiry, address, decision.capitalize()])

                # Store warnings separately
                if "warning" in license_data:
                    for warning in license_data["warning"]:
                        warnings_results.append([full_name, warning["description"], warning["confidence"], warning["decision"]])

        # Display Driver's License Table
        if license_results:
            license_df = pd.DataFrame(license_results, columns=["Full Name", "License Number", "Date of Birth", "Expiry Date", "Address", "Verification Status"])
            st.table(license_df)

        # Display Warnings
        if warnings_results:
            st.warning("⚠️ Warnings Found:")
            warnings_df = pd.DataFrame(warnings_results, columns=["Full Name", "Warning", "Confidence", "Decision"])
            st.table(warnings_df)

        # Decision Output
        rejected = any(decision == "reject" for _, _, _, _, _, decision in license_results)
        review_required = any(decision == "review" for _, _, _, _, _, decision in license_results)

        if rejected:
            st.error("❌ One or more licenses were **REJECTED**.")
        elif review_required:
            st.warning("🔍 Some licenses require **MANUAL REVIEW**.")
        else:
            st.success("✅ All uploaded licenses **PASSED VERIFICATION**!")
