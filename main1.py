import streamlit as st
import psycopg2
import os
import google.generativeai as genai
import time

# --- API Configuration ---
# Set your Gemini API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyATctANfRiXQb5F0kD8nVbynkMejkAjkbI"))

# --- Default DB Configuration (editable in Streamlit) ---
DB_HOST = "localhost"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "postgres123"

# --- Helper Functions ---

def get_db_connection():
    """Establishes and returns a PostgreSQL database connection."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return None

def fetch_customers_with_weather(conn):
    """Fetches customer and weather alert data."""
    customers = []
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT p.party_name, p.party_type, p.policy_type, p.zipcode, p.email,
                       w.alert_event, w.description, w.sender_name, w.alert_start, w.alert_end
                FROM party p
                LEFT JOIN weather_alerts w ON p.zipcode = w.zipcode
            """)
            customers = cur.fetchall()
            cur.close()
        except Exception as e:
            st.error(f"Error fetching customers and weather: {e}")
    return customers

def map_alert_to_policy(alert_event):
    """Maps a weather alert event to relevant policy types."""
    alert_event_lower = (alert_event or "").lower()
    relevant_policies = []

    if any(keyword in alert_event_lower for keyword in ['hurricane', 'typhoon', 'tropical storm', 'flood', 'flash flood', 'storm surge']):
        relevant_policies.extend(['home', 'property'])
    if any(keyword in alert_event_lower for keyword in ['tornado', 'severe thunderstorm', 'hail', 'high wind', 'wind advisory', 'blizzard', 'ice storm']):
        relevant_policies.extend(['home', 'property', 'auto insurance'])
    if any(keyword in alert_event_lower for keyword in ['winter storm', 'heavy snow', 'freezing rain']):
        relevant_policies.extend(['home', 'auto insurance'])
    if any(keyword in alert_event_lower for keyword in ['fire', 'wildfire']):
        relevant_policies.append('property')
    if any(keyword in alert_event_lower for keyword in ['heat advisory', 'extreme heat']):
        relevant_policies.append('home')
    if any(keyword in alert_event_lower for keyword in ['earthquake', 'tsunami']):
        relevant_policies.extend(['home', 'property'])

    return list(set(relevant_policies))

def generate_email_with_gemini(customer_name, policy_type, alert_details):
    """Generates a personalized email using Gemini 1.5 Flash model."""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        st.error(f"Error initializing Gemini model: {e}")
        return "Error: Gemini model not configured or failed to initialize."

    prompt = f"""
    You are an AI assistant for ABCD Insurance.
    Generate a concise and helpful email to a customer regarding a severe weather alert.

    Customer Name: {customer_name}
    Customer Policy Type: {policy_type}
    Severe Weather Alert Details:
    - Event: {alert_details.get('event', 'N/A')}
    - Description: {alert_details.get('description', 'N/A')}
    - Sender: {alert_details.get('sender_name', 'N/A')}
    - Start Time: {time.ctime(alert_details.get('start', 0))} UTC
    - End Time: {time.ctime(alert_details.get('end', 0))} UTC

    The email should:
    1. Greet the customer by name.
    2. Clearly state the severe weather alert.
    3. Briefly explain how this alert might be relevant to their specific {policy_type} policy.
    4. Advise them on general safety precautions or actions related to their policy.
    5. Offer assistance and provide a call to action (e.g., "contact us if you have questions").
    6. Be professional and empathetic.
    7. Keep it under 200 words.
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        st.error(f"Error generating content with Gemini: {e}")
        return "Error: Failed to generate email content."

# --- Streamlit UI ---

st.set_page_config(page_title="ABCD Insurance Weather Alert System", layout="wide")
st.title("⛈️ ABCD Insurance: Personalized Weather Alert Emails 📧")
st.markdown("""
This application helps ABCD Insurance identify customers affected by severe weather alerts
and generate personalized emails using Gemini 2.5 Flash LLM.
""")

# --- Configuration Inputs ---
st.header("1. Configuration")
with st.expander("PostgreSQL Database Credentials"):
    st.info("Enter your PostgreSQL database connection details.")
    db_host_input = st.text_input("DB Host", value=DB_HOST, key="db_host")
    db_name_input = st.text_input("DB Name", value=DB_NAME, key="db_name")
    db_user_input = st.text_input("DB User", value=DB_USER, key="db_user")
    db_password_input = st.text_input("DB Password", type="password", value=DB_PASSWORD, key="db_password")

    # Update global variables with user input
    globals()['DB_HOST'] = db_host_input
    globals()['DB_NAME'] = db_name_input
    globals()['DB_USER'] = db_user_input
    globals()['DB_PASSWORD'] = db_password_input

st.markdown("---")

# --- Main Logic ---
st.header("2. Generate Weather Alerts & Emails")

if st.button("Fetch Alerts and Generate Emails", help="Click to connect to DB, fetch weather alerts, and generate emails."):
    if not DB_HOST or not DB_NAME or not DB_USER or not DB_PASSWORD:
        st.error("Please provide all PostgreSQL database credentials.")
    else:
        st.info("Connecting to database and fetching customer data...")
        conn = get_db_connection()
        if conn:
            customers_data = fetch_customers_with_weather(conn)
            conn.close()

            if customers_data:
                st.success(f"Successfully fetched {len(customers_data)} customers from the database.")
                st.info("Generating personalized emails. This may take a moment...")

                generated_emails = []

                for i, customer in enumerate(customers_data):
                    party_name, party_type, policy_type, zipcode, email, alert_event, description, sender_name, alert_start, alert_end = customer

                    if alert_event:
                        relevant_policies = map_alert_to_policy(alert_event)
                        if policy_type.lower() in relevant_policies:
                            st.success(f"Match found! Policy '{policy_type}' is relevant to alert: '{alert_event}'")
                            alert_details = {
                                "event": alert_event,
                                "description": description,
                                "sender_name": sender_name,
                                "start": alert_start,
                                "end": alert_end
                            }
                            with st.spinner(f"Generating email for {party_name} about {alert_event}..."):
                                email_content = generate_email_with_gemini(
                                    customer_name=party_name,
                                    policy_type=policy_type,
                                    alert_details=alert_details
                                )
                                generated_emails.append({
                                    "customer_name": party_name,
                                    "email": email,
                                    "policy_type": policy_type,
                                    "alert_event": alert_event,
                                    "generated_email_body": email_content
                                })
                        else:
                            st.info(f"Alert '{alert_event}' not directly relevant to '{policy_type}' policy.")
                    else:
                        st.info(f"No active severe weather alerts for zipcode {zipcode}.")

                # Display Generated Emails
                st.markdown("---")
                st.header("3. Generated Personalized Emails")

                if generated_emails:
                    for i, email_data in enumerate(generated_emails):
                        st.subheader(f"Email {i+1}: To {email_data['customer_name']} ({email_data['email']})")
                        st.markdown(f"**Policy Type:** {email_data['policy_type']}")
                        st.markdown(f"**Weather Alert:** {email_data['alert_event']}")
                        st.text_area("Email Content", email_data['generated_email_body'], height=300, key=f"email_content_{i}")
                        st.markdown("---")
                else:
                    st.info("No relevant weather alerts found for your customers, or no emails were generated.")
            else:
                st.warning("No customers found in the 'party' table. Please ensure your database is populated.")
        else:
            st.error("Could not establish a database connection. Please check your credentials.")
