import firebase_admin
from firebase_admin import credentials, firestore, db, auth
from firebase_functions import https_fn
from firebase_functions.firestore_fn import on_document_written

firebase_admin.initialize_app()

@https_fn.on_request()
def cleanup_user_data(request):
    uid = request.json.get("uid")

    if not uid:
        return "UID not provided", 400

    # Initialize Firestore Client
    firestore_db = firestore.client()

    # Realtime Database references
    devices_ref = db.reference(f"devices/{uid}")
    rooms_ref = db.reference(f"rooms/{uid}")
    spaces_ref = db.reference(f"spaces/{uid}")

    # Firestore references
    user_doc_ref = firestore_db.collection("users").document(uid)
    environmental_data_ref = firestore_db.collection("environmental_data").document(uid).collections()

    try:
        user_doc_ref.delete()
        for collection in environmental_data_ref:
            for doc in collection.stream():
                doc.reference.delete()
        print(f"Deleted Firestore data for user: {uid} from 'users' and 'environmental_data' documents")

        devices_ref.delete()
        rooms_ref.delete()
        spaces_ref.delete()
        print(f"Deleted Realtime Database data for user: {uid} from devices, rooms, and spaces")

        return f"Successfully deleted user data for {uid}", 200

    except Exception as e:
        print(f"Error deleting user data for {uid}: {str(e)}")
        return f"Error deleting user data for {uid}: {str(e)}", 500

def update_total_power_consumption(device_id, firestore_db):
    periods = ["last_week", "last_month", "last_year"]

    try:
        for period in periods:
            # Reference to the history collection
            history_ref = firestore_db.collection("device_history").document(device_id).collection("history")

            # Sum the power_consumption values
            total_power_consumption = 0
            for start_time_doc in history_ref.stream():
                data = start_time_doc.to_dict()
                power_consumption_value = data.get("power_consumption")
                if power_consumption_value is not None:
                    total_power_consumption += power_consumption_value

            # Reference to the period collection and document
            period_ref = firestore_db.collection(period).document(device_id)

            # Update the period document with total_power_consumption
            period_ref.set({"total_power_consumption": total_power_consumption}, merge=True)

            print(f"Updated total_power_consumption for device_id: {device_id} in period: {period} with value: {total_power_consumption}")

    except Exception as e:
        print(f"Error updating total_power_consumption for device_id: {device_id}: {str(e)}")

@on_document_written(document="device_history/{device_id}/{history}/{start_time}")
def on_device_history_written(event):
    # Initialize Firestore client
    firestore_db = firestore.client()

    # Get the document that triggered the function
    device_id = event.params["device_id"]
    start_time = event.params["start_time"]
    document = event.data.after

    if not document:
        print(f"No document found for device_id: {device_id} and start_time: {start_time}")
        return

    print(f"Document data: {document}")
    print(f"Document data (dict): {document.to_dict() if document else 'None'}")

    # Define the new collections
    new_collections = ["last_week", "last_month", "last_year"]

    try:
        for new_collection in new_collections:
            # Reference to the new collection
            new_collection_ref = firestore_db.collection(new_collection).document(device_id).collection("history").document(start_time)

            # Copy the data to the new collection
            new_collection_ref.set(document.to_dict())

            # Copy subcollections
            for subcollection in document.reference.collections():
                for subdoc in subcollection.stream():
                    new_subcollection_ref = new_collection_ref.collection(subcollection.id).document(subdoc.id)
                    new_subcollection_ref.set(subdoc.to_dict())

        print(f"Copied data for device_id: {device_id} and start_time: {start_time} to {', '.join(new_collections)} collections")

        # Update total power consumption
        update_total_power_consumption(device_id, firestore_db)

    except Exception as e:
        print(f"Error copying data for device_id: {device_id} and start_time: {start_time}: {str(e)}")