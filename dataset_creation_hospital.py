import pandas as pd
import numpy as np
import random
import json
from datetime import datetime, timedelta

# -----------------------------
# CONFIGURATION
# -----------------------------
NUM_PATIENTS = 50
NUM_APPOINTMENTS = 1000     # Increase rows here (main dataset)
NUM_LOG_EVENTS = 1200      # Conversation / interaction logs volume
START_DATE = datetime(2024, 1, 1)

clinics = ["HealthFirst Clinic", "CarePlus Hospital", "Sunrise Medical", "CityCare Center"]
departments = ["General Medicine", "Cardiology", "Dermatology", "Orthopedics", "ENT", "Pediatrics", "Gynecology"]
doctors = [
    "Dr. A. Rao", "Dr. S. Iyer", "Dr. M. Gupta", "Dr. N. Banerjee",
    "Dr. P. Mehta", "Dr. R. Singh", "Dr. K. Nair", "Dr. T. Das"
]

visit_types = [
    "New Consultation",
    "Follow-up",
    "Lab Test",
    "Vaccination",
    "Teleconsultation",
    "Annual Checkup"
]

appointment_statuses = ["SCHEDULED", "RESCHEDULED", "CANCELLED", "COMPLETED", "NO_SHOW"]
channels = ["WhatsApp", "SMS", "Email", "Phone", "In-app Chat"]

# Common patient intents (for logs)
intents = [
    "SCHEDULE_APPOINTMENT",
    "RESCHEDULE_APPOINTMENT",
    "CANCEL_APPOINTMENT",
    "CHECK_AVAILABILITY",
    "ASK_PREP_INSTRUCTIONS",
    "ASK_POST_VISIT_CARE",
    "ASK_CLINIC_POLICY",
    "VIEW_APPOINTMENT"
]

# Simple prep instructions by visit type
prep_by_visit = {
    "New Consultation": "Bring previous medical reports (if any) and a list of current medications.",
    "Follow-up": "Bring your last prescription and any recent test reports.",
    "Lab Test": "If fasting is required, avoid food for 8–10 hours; water is allowed.",
    "Vaccination": "Carry a valid ID; inform staff about allergies or prior reactions.",
    "Teleconsultation": "Ensure a stable internet connection and be in a quiet place.",
    "Annual Checkup": "Arrive 15 minutes early; fasting may be required for blood tests."
}

post_care_by_dept = {
    "General Medicine": "Follow prescribed medicines and monitor symptoms; return if symptoms worsen.",
    "Cardiology": "Avoid strenuous activity if advised; track BP/heart rate as directed.",
    "Dermatology": "Apply topical medicines as instructed; avoid known irritants.",
    "Orthopedics": "Rest the affected area; follow physiotherapy guidance if provided.",
    "ENT": "Stay hydrated; avoid irritants like smoke; follow medication schedule.",
    "Pediatrics": "Monitor temperature and hydration; follow dosing instructions carefully.",
    "Gynecology": "Follow hygiene guidance; track symptoms and follow medication instructions."
}

policies = [
    "You can reschedule up to 2 hours before the appointment time.",
    "Please arrive 10–15 minutes early for in-person appointments.",
    "Cancellations are free up to 2 hours before the appointment.",
    "Teleconsultation links are shared 15 minutes before the slot."
]

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def random_timestamp_within_year():
    minutes = random.randint(0, 60 * 24 * 365)
    return START_DATE + timedelta(minutes=minutes)

def random_future_timestamp(base_ts, min_days=0, max_days=60):
    # used for follow-ups / reminders relative to appointment
    return base_ts + timedelta(days=random.randint(min_days, max_days), minutes=random.randint(0, 180))

def random_phone():
    return f"+91{random.randint(6000000000, 9999999999)}"

def random_email(first, last):
    domains = ["gmail.com", "outlook.com", "yahoo.com", "example.com"]
    return f"{first.lower()}.{last.lower()}{random.randint(1,999)}@{random.choice(domains)}"

def choose_slot(day_ts):
    # "scheduling system" simulation: slots between 9am-6pm every 15 mins
    start_hour = 9
    end_hour = 18
    slot_minute = random.choice([0, 15, 30, 45])
    hour = random.randint(start_hour, end_hour - 1)
    return day_ts.replace(hour=hour, minute=slot_minute, second=0, microsecond=0)

def generate_patient_name():
    first_names = ["Aarav","Vihaan","Ishaan","Saanvi","Ananya","Diya","Riya","Kabir","Arjun","Meera","Rahul","Priya","Neha","Karan","Pooja","Sneha"]
    last_names = ["Sharma","Verma","Iyer","Nair","Gupta","Mehta","Das","Banerjee","Singh","Khan","Patel","Joshi","Roy","Chatterjee"]
    first = random.choice(first_names)
    last = random.choice(last_names)
    return first, last

def make_nl_message(intent, patient_name, appt_id=None, dept=None, when=None):
    # light templates for interaction logs
    if intent == "SCHEDULE_APPOINTMENT":
        return f"Hi, I’m {patient_name}. I want to book an appointment{f' for {dept}' if dept else ''}{f' on {when}' if when else ''}."
    if intent == "RESCHEDULE_APPOINTMENT":
        return f"Hi, I need to reschedule my appointment{f' (ID {appt_id})' if appt_id else ''}. Can you move it to another slot?"
    if intent == "CANCEL_APPOINTMENT":
        return f"Please cancel my appointment{f' (ID {appt_id})' if appt_id else ''}."
    if intent == "CHECK_AVAILABILITY":
        return f"Do you have availability{f' for {dept}' if dept else ''} this week?"
    if intent == "ASK_PREP_INSTRUCTIONS":
        return f"What should I do to prepare for my visit{f' (ID {appt_id})' if appt_id else ''}?"
    if intent == "ASK_POST_VISIT_CARE":
        return f"Any guidance for after my visit{f' (ID {appt_id})' if appt_id else ''}?"
    if intent == "ASK_CLINIC_POLICY":
        return "What’s your reschedule/cancellation policy?"
    if intent == "VIEW_APPOINTMENT":
        return f"Can you show my upcoming appointments, I’m {patient_name}?"
    return "Hello"

def make_agent_reply(intent, dept=None, visit_type=None, appt_id=None, prep=None, post=None):
    if intent == "SCHEDULE_APPOINTMENT":
        return f"Sure — I can help you book. Please confirm your preferred department and visit type. Available slots are shown in the next step."
    if intent == "CHECK_AVAILABILITY":
        return f"Yes. I can check slots{f' for {dept}' if dept else ''}. Do you prefer morning or afternoon?"
    if intent == "RESCHEDULE_APPOINTMENT":
        return f"Got it. Please confirm a preferred date/time window and I’ll suggest the closest available slots{f' for appointment {appt_id}' if appt_id else ''}."
    if intent == "CANCEL_APPOINTMENT":
        return f"Okay — I can cancel{f' appointment {appt_id}' if appt_id else ''}. Please confirm to proceed."
    if intent == "ASK_PREP_INSTRUCTIONS":
        return prep or "Please arrive 10–15 minutes early and carry any relevant reports."
    if intent == "ASK_POST_VISIT_CARE":
        return post or "Follow your doctor’s advice and medications; contact the clinic if symptoms worsen."
    if intent == "ASK_CLINIC_POLICY":
        return random.choice(policies)
    if intent == "VIEW_APPOINTMENT":
        return "Sure — please confirm your phone number or email so I can locate your records."
    return "How can I help?"

# -----------------------------
# PATIENTS TABLE
# -----------------------------
patients = []
for pid in range(1, NUM_PATIENTS + 1):
    first, last = generate_patient_name()
    patient_name = f"{first} {last}"
    age = int(np.clip(np.random.normal(38, 16), 1, 90))
    preferred_channel = random.choice(channels)
    patients.append({
        "patient_id": pid,
        "patient_name": patient_name,
        "age": age,
        "gender": random.choice(["F", "M", "Other"]),
        "phone": random_phone(),
        "email": random_email(first, last),
        "preferred_channel": preferred_channel,
        "created_at": random_timestamp_within_year().strftime("%Y-%m-%d %H:%M:%S")
    })

df_patients = pd.DataFrame(patients)

# -----------------------------
# APPOINTMENTS TABLE
# -----------------------------
appointments = []
for appt_id in range(1, NUM_APPOINTMENTS + 1):
    patient = random.choice(patients)
    clinic = random.choice(clinics)
    dept = random.choice(departments)
    doctor = random.choice(doctors)
    visit_type = random.choice(visit_types)

    # create an appointment datetime (day chosen randomly within year, then pick a slot)
    base_day = random_timestamp_within_year().replace(hour=0, minute=0, second=0, microsecond=0)
    scheduled_time = choose_slot(base_day)

    status = random.choices(
        appointment_statuses,
        weights=[0.58, 0.12, 0.10, 0.15, 0.05],  # bias towards scheduled/completed
        k=1
    )[0]

    # If rescheduled, create old time
    original_time = None
    reschedule_reason = None
    if status == "RESCHEDULED":
        original_time = scheduled_time - timedelta(days=random.randint(1, 14))
        reschedule_reason = random.choice(["Patient request", "Doctor unavailable", "Clinic delay", "Emergency"])

    # If completed, add follow-up suggestion (sometimes)
    followup_recommended = (status == "COMPLETED" and random.random() < 0.35)

    # Reminders scheduling
    reminder_24h = scheduled_time - timedelta(hours=24)
    reminder_2h = scheduled_time - timedelta(hours=2)

    appointments.append({
        "appointment_id": appt_id,
        "patient_id": patient["patient_id"],
        "patient_name": patient["patient_name"],
        "clinic": clinic,
        "department": dept,
        "doctor": doctor,
        "visit_type": visit_type,
        "scheduled_datetime": scheduled_time.strftime("%Y-%m-%d %H:%M:%S"),
        "original_datetime": original_time.strftime("%Y-%m-%d %H:%M:%S") if original_time else "",
        "status": status,
        "channel": patient["preferred_channel"],
        "reason": reschedule_reason if reschedule_reason else "",
        "prep_instructions": prep_by_visit.get(visit_type, ""),
        "reminder_24h_at": reminder_24h.strftime("%Y-%m-%d %H:%M:%S"),
        "reminder_2h_at": reminder_2h.strftime("%Y-%m-%d %H:%M:%S"),
        "followup_recommended": followup_recommended,
        "followup_due_date": (scheduled_time + timedelta(days=random.choice([7, 14, 30]))).strftime("%Y-%m-%d")
                             if followup_recommended else ""
    })

df_appts = pd.DataFrame(appointments)

# Sort by scheduled datetime
df_appts["scheduled_datetime"] = pd.to_datetime(df_appts["scheduled_datetime"])
df_appts = df_appts.sort_values("scheduled_datetime")

# -----------------------------
# FAQ / COMMON QUERIES TABLE
# -----------------------------
faq = [
    {"category": "Reschedule", "query": "How do I reschedule my appointment?", "response": "Share your appointment ID and preferred date/time window. I’ll suggest available slots."},
    {"category": "Cancel", "query": "Can I cancel my appointment?", "response": "Yes. Please provide the appointment ID. Cancellations are free up to 2 hours before the slot."},
    {"category": "Prep", "query": "Do I need to fast before a blood test?", "response": "Some tests require 8–10 hours fasting. Water is usually allowed. I can confirm for your specific test."},
    {"category": "Arrival", "query": "How early should I arrive?", "response": "Please arrive 10–15 minutes early for in-person visits."},
    {"category": "Teleconsultation", "query": "When will I get the teleconsultation link?", "response": "The link is shared about 15 minutes before the scheduled slot."},
    {"category": "Reports", "query": "What documents should I bring?", "response": "Bring previous reports, prescriptions, and a list of current medications."},
    {"category": "Post-care", "query": "What should I do after my visit?", "response": "Follow prescribed medicines and instructions. Contact the clinic if symptoms worsen."},
]
df_faq = pd.DataFrame(faq)

# -----------------------------
# INTERACTION LOGS (JSONL)
# Each line = one event with user msg, agent msg, action, and outcome
# -----------------------------
log_events = []
appt_ids = df_appts["appointment_id"].tolist()

def pick_existing_appt_for_patient(patient_id):
    # quick sampling: try a few times
    for _ in range(10):
        row = df_appts.sample(1).iloc[0]
        if int(row["patient_id"]) == int(patient_id):
            return row
    # fallback
    return df_appts.sample(1).iloc[0]

for event_id in range(1, NUM_LOG_EVENTS + 1):
    patient = random.choice(patients)
    dept = random.choice(departments)
    visit_type = random.choice(visit_types)
    intent = random.choice(intents)

    # Decide if this intent should attach an existing appointment
    appt_row = None
    appt_id = None
    if intent in ["RESCHEDULE_APPOINTMENT", "CANCEL_APPOINTMENT", "ASK_PREP_INSTRUCTIONS", "ASK_POST_VISIT_CARE"]:
        appt_row = pick_existing_appt_for_patient(patient["patient_id"])
        appt_id = int(appt_row["appointment_id"])

    # Timestamps for log event
    event_ts = random_timestamp_within_year()

    user_msg = make_nl_message(intent, patient["patient_name"], appt_id=appt_id, dept=dept, when="next Monday morning")
    prep = prep_by_visit.get(appt_row["visit_type"], "") if appt_row is not None else prep_by_visit.get(visit_type, "")
    post = post_care_by_dept.get(appt_row["department"], "") if appt_row is not None else post_care_by_dept.get(dept, "")
    agent_msg = make_agent_reply(intent, dept=dept, visit_type=visit_type, appt_id=appt_id, prep=prep, post=post)

    # Simulate action + outcome
    action = None
    outcome = "INFO_ONLY"
    appointment_update = {}

    if intent == "SCHEDULE_APPOINTMENT":
        action = "CREATE_APPOINTMENT"
        # create a "new" appointment reference (not inserted into appt table to keep generation fast)
        new_appt_time = choose_slot(random_future_timestamp(event_ts).replace(hour=0, minute=0, second=0, microsecond=0))
        outcome = random.choices(["SUCCESS", "NEED_MORE_INFO", "NO_SLOTS"], weights=[0.75, 0.20, 0.05], k=1)[0]
        appointment_update = {
            "proposed_department": dept,
            "proposed_visit_type": visit_type,
            "proposed_datetime": new_appt_time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "PENDING_CONFIRMATION" if outcome != "SUCCESS" else "SCHEDULED"
        }

    elif intent == "CHECK_AVAILABILITY":
        action = "LIST_SLOTS"
        outcome = random.choices(["SUCCESS", "NO_SLOTS"], weights=[0.9, 0.1], k=1)[0]
        appointment_update = {
            "department": dept,
            "slots_preview": [
                choose_slot((event_ts + timedelta(days=d)).replace(hour=0, minute=0, second=0, microsecond=0)).strftime("%Y-%m-%d %H:%M:%S")
                for d in random.sample(range(1, 10), 3)
            ] if outcome == "SUCCESS" else []
        }

    elif intent == "RESCHEDULE_APPOINTMENT":
        action = "RESCHEDULE_APPOINTMENT"
        outcome = random.choices(["SUCCESS", "NOT_FOUND", "TOO_LATE", "NO_SLOTS"], weights=[0.78, 0.06, 0.10, 0.06], k=1)[0]
        if appt_row is not None:
            old_dt = pd.to_datetime(appt_row["scheduled_datetime"])
            new_dt = choose_slot((old_dt + timedelta(days=random.randint(1, 10))).replace(hour=0, minute=0, second=0, microsecond=0))
            appointment_update = {
                "appointment_id": appt_id,
                "old_datetime": old_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "new_datetime": new_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "RESCHEDULED" if outcome == "SUCCESS" else "UNCHANGED"
            }

    elif intent == "CANCEL_APPOINTMENT":
        action = "CANCEL_APPOINTMENT"
        outcome = random.choices(["SUCCESS", "NOT_FOUND", "TOO_LATE"], weights=[0.85, 0.08, 0.07], k=1)[0]
        appointment_update = {
            "appointment_id": appt_id,
            "status": "CANCELLED" if outcome == "SUCCESS" else "UNCHANGED"
        }

    elif intent == "VIEW_APPOINTMENT":
        action = "FETCH_APPOINTMENTS"
        outcome = random.choices(["SUCCESS", "NEED_VERIFICATION"], weights=[0.7, 0.3], k=1)[0]
        appointment_update = {"patient_id": patient["patient_id"], "result_count": random.randint(0, 4)}

    log_events.append({
        "event_id": event_id,
        "timestamp": event_ts.strftime("%Y-%m-%d %H:%M:%S"),
        "patient_id": patient["patient_id"],
        "patient_name": patient["patient_name"],
        "channel": patient["preferred_channel"],
        "intent": intent,
        "user_message": user_msg,
        "agent_message": agent_msg,
        "action": action,
        "outcome": outcome,
        "appointment_update": appointment_update
    })

# -----------------------------
# SAVE FILES
# -----------------------------
patients_file = "synthetic_patients.csv"
appts_file = "synthetic_appointments.csv"
faq_file = "synthetic_faq.csv"
logs_file = "synthetic_interaction_logs.jsonl"

df_patients.to_csv(patients_file, index=False)

# convert datetime back to string for CSV consistency
df_appts_out = df_appts.copy()
df_appts_out["scheduled_datetime"] = df_appts_out["scheduled_datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
df_appts_out.to_csv(appts_file, index=False)

df_faq.to_csv(faq_file, index=False)

with open(logs_file, "w", encoding="utf-8") as f:
    for e in log_events:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")

print("\n✅ Synthetic healthcare datasets created successfully!")
print(f"Patients:     {len(df_patients)} rows -> {patients_file}")
print(f"Appointments: {len(df_appts_out)} rows -> {appts_file}")
print(f"FAQ:          {len(df_faq)} rows -> {faq_file}")
print(f"Logs:         {len(log_events)} events -> {logs_file}")

print("\nSample Patients:")
print(df_patients.head())

print("\nSample Appointments:")
print(df_appts_out.head())

print("\nSample Log Event (JSON):")
print(json.dumps(log_events[0], indent=2, ensure_ascii=False))