import firebase_admin
from firebase_admin import credentials, firestore, db, auth
from firebase_functions import https_fn

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
    environmental_data_ref = firestore_db.collection("environmental_data").document(uid)

    try:
        user_doc_ref.delete()
        environmental_data_ref.delete()
        print(f"Deleted Firestore data for user: {uid} from 'users' and 'environmental_data' documents")

        devices_ref.delete()
        rooms_ref.delete()
        spaces_ref.delete()
        print(f"Deleted Realtime Database data for user: {uid} from devices, rooms, and spaces")

        return f"Successfully deleted user data for {uid}", 200

    except Exception as e:
        print(f"Error deleting user data for {uid}: {str(e)}")
        return f"Error deleting user data for {uid}: {str(e)}", 500