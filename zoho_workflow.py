import os

import requests
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
# It's recommended to use environment variables for sensitive data
ZOHO_CLIENT_ID = os.environ.get("ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = os.environ.get("ZOHO_CLIENT_SECRET")
ZOHO_REFRESH_TOKEN = os.environ.get("ZOHO_REFRESH_TOKEN")
ZOHO_PROJECT_ID = os.environ.get("ZOHO_PROJECT_ID")
ZOHO_PORTAL_ID = os.environ.get("ZOHO_PORTAL_ID")
ZOHO_ACCOUNTS_BASE = os.environ.get("ZOHO_ACCOUNTS_BASE", "https://accounts.zoho.com")


def get_access_token():
    """
    Refreshes the Zoho API access token using the refresh token.
    """
    url = f"{ZOHO_ACCOUNTS_BASE}/oauth/v2/token"
    data = {
        "refresh_token": ZOHO_REFRESH_TOKEN,
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token",
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]


def get_project_documents(access_token):
    """
    Fetches the list of documents from a Zoho Project.
    This is a placeholder function. The actual implementation will require
    interacting with both Zoho Projects and Zoho WorkDrive APIs.
    """
    print("Fetching project documents...")
    # This is a simplified representation.
    # In reality, you would need to:
    # 1. Find the WorkDrive folder associated with the project.
    # 2. List the files in that folder using the WorkDrive API.
    # For now, we'll return a mock list of documents.
    return [
        {"id": "doc1", "name": "Requirement Specification.docx", "author": "author1@example.com"},
        {"id": "doc2", "name": "Design Document.pdf", "author": "author2@example.com"},
        # Missing extension
        {"id": "doc3", "name": "Meeting Notes", "author": "author3@example.com"},
    ]


def assess_document_quality(document):
    """
    Assesses the quality of a document based on predefined criteria.
    """
    print(f"Assessing document: {document['name']}")
    issues = []
    # Example check 1: Check for file extension
    if "." not in document["name"]:
        issues.append("Missing file extension.")

    # Example check 2: Check for document title (very basic)
    # A more advanced check would involve opening the document and checking its content.
    if len(document["name"].split(".")[0]) < 5:
        issues.append("Document title is too short.")

    return issues


def draft_email_to_author(document, issues):
    """
    Drafts an email to the document author with a list of issues.
    """
    print(f"Drafting email to: {document['author']}")
    subject = f"Review of your document: {document['name']}"
    body = f"""
    Hello,

    I have reviewed the document '{document["name"]}' that you uploaded to the project.
    I have the following queries and requests for clarification:

    - {"- ".join(issues)}

    Could you please address these points?

    Thanks,
    Agentic Workflow
    """
    return {"to": document["author"], "subject": subject, "body": body}


def main():
    """
    Main function to run the agentic workflow.
    """
    print("Starting agentic workflow...")
    try:
        access_token = get_access_token()
        documents = get_project_documents(access_token)

        for doc in documents:
            issues = assess_document_quality(doc)
            if issues:
                email = draft_email_to_author(doc, issues)
                print("--- New Email Draft ---")
                print(f"To: {email['to']}")
                print(f"Subject: {email['subject']}")
                print(f"Body: {email['body']}")
                print("-----------------------")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
