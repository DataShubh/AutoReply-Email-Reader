import streamlit as st
import pymongo
import imaplib
from datetime import datetime, timedelta
import email
from email.header import decode_header
import re
from dateutil import parser


# Initialize connection.
# Uses st.cache_resource to only run once
@st.cache_resource
def init_connection():
    # db_username = st.secrets.db_username
    # db_password = st.secrets.db_password

    # mongo_uri_template = "mongodb+srv://{username}:{password}@emailreader.elzbauk.mongodb.net/"
    # mongo_uri = mongo_uri_template.format(username=db_username, password=db_password)

    # client = pymongo.MongoClient(mongo_uri)
    return pymongo.MongoClient("mongodb+srv://Vedsu:CVxB6F2N700cQ0qu@cluster0.thbmwqi.mongodb.net/")

client = init_connection()
db = client.EmailDatabase
collection_email = db.email
collection_search = db.Searchwords
collection_user = db.user

def fetch_user_info(email):
    user_info = collection_user.find_one({"emailid": email})
    return user_info

def main():
    st.subheader("Email Selector")

    # Get list of emails from database
    email_list = [user["emailid"] for user in collection_user.find({}, {"emailid": 1})]
    cols1, cols2 = st.columns(2)
    
    with cols1:
    
        # Dropdown to select email
        selected_email = st.selectbox("Select your email", email_list)
    
    with cols2:
    
        # Dropdown to select number of days
        selected_option = st.number_input("Select number of days")
    
        no_of_days = int(selected_option)
    
        # Display selected number of days
        if no_of_days:
    
            st.info(f"Selected days : {no_of_days}")
    
    # Fetch and display selected email's information
    if selected_email:
    
        user_info = fetch_user_info(selected_email)
    
        if user_info:
            # st.subheader("Selected Email Information")cl
            with cols1:
                st.info(f"Selected email: {user_info["emailid"]}")
            # st.write("Password:", user_info["password"])
            # st.write("Host Name:", user_info["imapserver"])
            if st.button("Sync autoreply"):
                emailid, passowrdid, imap_server_id, no_of_days = user_info["emailid"],user_info["password"],user_info["imapserver"],no_of_days
                fetch_emails(emailid, passowrdid, imap_server_id, no_of_days)
            
        else:
            st.error("User information not found.")



# Function to find all email addresses in the description field of emails
def find_emails_in_description(description):
    # Regex pattern to find email addresses
    email_pattern = r'[\w\.-]+@[\w\.-]+'
    
    # Find all email addresses using regex
    email_addresses = re.findall(email_pattern, description)
    
    return email_addresses


def fetch_emails(emailid, passowrdid, imap_server_id, no_of_days):
    document_to_insert =[ ]
    inbox_status = None
    spam_status = None
    
    bar = st.progress(1)
    
    try: 
    
        imap_server = imaplib.IMAP4_SSL(host=imap_server_id)
    
        imap_server.login(emailid, passowrdid)

        # Default is Inbox 
        status, messages = imap_server.select()

        # Calculate the date 5 days ago
        since_date = (datetime.now()-timedelta(days=no_of_days)).strftime("%d-%b-%Y")

        # Create a search criteria to fetch emails sent since the calculated date
        search_criteria = f'SINCE {since_date}'

        # Search for emails based on search criteria
        status, message_number_raw = imap_server.search(None, search_criteria)

        message_number_list = message_number_raw[0].split()

        st.write("Inbox:", int(len(message_number_list)))
        
        bar.progress(5)

        for message_number in message_number_list:
            sender = None
            reciever = None
            date = None
            subject = None
            description = None

            text_string = message_number.decode('utf-8')

            number = int(text_string)

            res, msg = imap_server.fetch(str(number), "(RFC822)")

            for response in msg:
                try:
                    if isinstance(response, tuple):
                        # parse a bytes into a message object\
                        msg = email.message_from_bytes(response[1])

                        # decode email sender
                        From, encoding = decode_header(msg.get("from"))[0] 

                        sender= From

                        if isinstance(From, bytes):
                            From = From.decode(encoding)
                            sender = From
                        
                        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                        sender_matches = re.findall(email_pattern, sender)
                        
                        # Convert the list of matches to a single string, separated by a delimiter (e.g., comma)
                        sender = ', '.join(sender_matches)
                        
                        blocked_domains = ["mailer-daemon", "postmaster", "emailsecurity", "bounce", "info","billing", "help","support", "cs", "customer service","noreply"]
                        
                        if(sender.split('@')[0].lower() not in blocked_domains):

                            # decode the mail subject
                            Subject, encoding = decode_header(msg["subject"])[0]
                            
                            subject = Subject

                            if isinstance(Subject, bytes):
                                # if it's a bytes, decode to str
                                Subject = Subject.decode(encoding)
                                subject = Subject

                            # decode the email reciever
                            To, encoding = decode_header(msg["to"])[0]
                            reciever = To

                            if isinstance(To, bytes):

                                To = To.decode(encoding)
                                receiver = To
                            
                            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                            
                            reciever_matches = re.findall(email_pattern, reciever)

                            reciever = ', '.join(reciever_matches)    


                            Date, encoding = decode_header(msg["date"])[0]
                            
                            parsed_date = parser.parse(Date)
                            
                            date = parsed_date.strftime("%Y-%m-%d")
                                        
                            if isinstance(Date, bytes):
                                            
                                # if it's a bytes, decode to str
                                Date = Date.decode(encoding)
                                parsed_date = parser.parse(Date)
                                date = parsed_date.strftime("%Y-%m-%d")

                            # if the message is multipart
                            if msg.is_multipart():

                                for part in msg.walk():
                                    # extract content of email
                                    content_type = part.get_content_type()
                                    content_disposition = str(part.get("Content-Disposition"))
                                    try:
                                        body = part.get_payload(decode= True).decode()
                                    except:
                                        pass

                                    if content_type == "text/plain" and "attachment" not in content_disposition:
                                        description  = body
                                    elif "attachment" in content_disposition:
                                        pass
                            else:
                                content_type = msg.get_content_type()
                                body= msg.get_payload(decode=True).decode()
                                if content_type == "text/plain":
                                    description=body
                            
                            emails_found = find_emails_in_description(description)
                            
                            # designation, emails, remarks = extract_job_title(description)   
                            # new_document = {"sender":sender, "reciever":reciever , "date":date ,
                            #           "subject":subject, "description":description, "jobtitle":designation,"emails":emails, "remark":remarks}
                            new_document = {"sender":sender, "reciever":reciever , "date":date ,
                                      "subject":subject, "description":description,"emails":emails_found,}
                            
                            document_to_insert.append(new_document)
                except:
                    
                    pass                         
                
        try:
                collection_email.insert_many(document_to_insert)
                    
                st.info(f"Inbox Updated: {len(document_to_insert)}")
                    
                inbox_status = "updated"
                    
                
        except:
    
                st.info("No New mails in inbox")
                        
                inbox_status = "already updated"
                
    
    except imaplib.IMAP4.error:
                                
                st.error("failed to connect to inbox")
                
                inbox_status = "failed"
    
    bar.progress(25)
    
    document_to_insert =[]
    
    # Spam
    try: 
        imap_server = imaplib.IMAP4_SSL(host=imap_server_id)
        imap_server.login(emailid, passowrdid)

        # Default is Inbox 
        status, messages = imap_server.select('spam')

        # Calculate the date 5 days ago
        since_date = (datetime.now()-timedelta(days=no_of_days)).strftime("%d-%b-%Y")

        # Create a search criteria to fetch emails sent since the calculated date
        search_criteria = f'SINCE {since_date}'

        # Search for emails based on search criteria
        status, message_number_raw = imap_server.search(None, search_criteria)

        message_number_list = message_number_raw[0].split()

        st.write("Spam:", int(len(message_number_list)))
        bar.progress(40)

        for message_number in message_number_list:
            sender = None
            reciever = None
            date = None
            subject = None
            description = None

            text_string = message_number.decode('utf-8')

            number = int(text_string)

            res, msg = imap_server.fetch(str(number), "(RFC822)")

            for response in msg:
                try:
                    if isinstance(response, tuple):
                        # parse a bytes into a message object\
                        msg = email.message_from_bytes(response[1])

                        # decode email sender
                        From, encoding = decode_header(msg.get("from"))[0] 

                        sender= From

                        if isinstance(From, bytes):
                            From = From.decode(encoding)
                            sender = From
                        
                        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                        sender_matches = re.findall(email_pattern, sender)
                        # Convert the list of matches to a single string, separated by a delimiter (e.g., comma)
                        sender = ', '.join(sender_matches)
                        blocked_domains = ["mailer-daemon", "postmaster", "emailsecurity", "bounce", "info","billing", "help","support", "cs", "customer service",]
                        if(sender.split('@')[0].lower() not in blocked_domains):

                            # decode the mail subject
                            Subject, encoding = decode_header(msg["subject"])[0]
                            subject = Subject

                            if isinstance(Subject, bytes):
                                # if it's a bytes, decode to str
                                Subject = Subject.decode(encoding)
                                subject = Subject

                            # decode the email reciever
                            To, encoding = decode_header(msg["to"])[0]
                            reciever = To

                            if isinstance(To, bytes):

                                To = To.decode(encoding)
                                receiver = To
                            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                            reciever_matches = re.findall(email_pattern, reciever)

                            reciever = ', '.join(reciever_matches)    


                            Date, encoding = decode_header(msg["date"])[0]
                            parsed_date = parser.parse(Date)
                            date = parsed_date.strftime("%Y-%m-%d")
                                        
                            if isinstance(Date, bytes):
                                            
                                # if it's a bytes, decode to str
                                Date = Date.decode(encoding)
                                parsed_date = parser.parse(Date)
                                date = parsed_date.strftime("%Y-%m-%d")

                            # if the message is multipart
                            if msg.is_multipart():

                                for part in msg.walk():
                                    # extract content of email
                                    content_type = part.get_content_type()
                                    content_disposition = str(part.get("Content-Disposition"))
                                    try:
                                        body = part.get_payload(decode= True).decode()
                                    except:
                                        pass

                                    if content_type == "text/plain" and "attachment" not in content_disposition:
                                        description  = body
                                    elif "attachment" in content_disposition:
                                        pass
                            else:
                                content_type = msg.get_content_type()
                                body= msg.get_payload(decode=True).decode()
                                if content_type == "text/plain":
                                    description=body
                            
                            emails_found = find_emails_in_description(description)
                            # designation, emails, remarks = extract_job_title(description)   
                            new_document = {"sender":sender, "reciever":reciever , "date":date ,
                                      "subject":subject, "description":description,"emails":emails_found}
                            document_to_insert.append(new_document)
                except:
                    
                    pass                         
        try:
                    collection_email.insert_many(document_to_insert)
                    
                    st.info(f"Spam Updated:, {len(document_to_insert)}")
                    
                    spam_status = "updated"
                    
                
        except:
    
                    st.info("No New mails in spam")
                        
                    spam_status = "already updated"
                
    except imaplib.IMAP4.error:
                                
                st.error("failed to connect to spam")
                
                spam_status = "failed"
    
    bar.progress(60)

    user_query = {"emailid":emailid}
    current_time = datetime.now()
    formatted_current_time  = current_time.strftime("%H:%M:%S")
    
    user_update = {"$set": {"inbox": inbox_status, "spam": spam_status, "lastupdated":formatted_current_time}}
    collection_user.update_one(user_query,user_update)
    
    bar.progress(70)
    
    pipeline = [ {
            "$group": {
                "_id": {
                    "sender": "$sender",
                    "description": "$description",
                    "reciever": "$reciever",
                    "subject":"$subject",
                    "date": "$date"
                },
                "duplicates": {"$addToSet": "$_id"},
                "count": {"$sum": 1}
                }
                },
                # Find documents with more than one occurrence    
                {"$match": {
                "count": {"$gt": 1}}
                }]
    
    
    # Find and remove duplicate documents based on the filter
    for doc in collection_email.aggregate(pipeline):
        # Keep one copy (first occurrence) and delete the rest
        duplicates_to_remove = doc["duplicates"][1:]
        collection_email.delete_many({"_id": {"$in": duplicates_to_remove}})
    bar.progress(75)
    
    # Query to extract data from the "Searchwords" collection
    search_words_data = collection_search.find({}, {"_id": 0, "keyword": 1})

    # Extract "keyword" values and store them in a list
    search_words_list = [item["keyword"] for item in search_words_data]
    
    keywords  = search_words_list
    job_titles = ["engineer", "executive", "assistant", "HR", "finance", "management", "account", "Audit", "Bill", "operations","Coordinator",
                   "developer", "analyst", "manager", "Admin","specialist","director", "president", "head", "officer","attorney","compliance" ]
    keyword_updates(keywords)
    bar.progress(90)

    jobtitle_update(job_titles)
    
    bar.progress(100)

def keyword_updates(keywords):
    
    
    # Perform text search for each keyword in the "description" and "subject" fields
    for keyword in keywords:
        # Construct the search query using the keyword
        query = {"$text": {"$search": keyword,"$caseSensitive": False}}  # Text search in description field
        collection_email.update_many(query,{"$addToSet": {"remark": keyword}})
    
  

def jobtitle_update(job_titles):
    # List of job titles to search for
    # job_titles = ["engineer", "developer", "analyst", "manager", "Admin","specialist","director", "president", "head", "officer","attorney","compliance" ]
    # Perform text search for each job title in the "jobTitle" field
    for job_title in job_titles:
        # Construct the search query using the job title
        query = {"description": {"$regex": job_title, "$options": "i"}}  # Case-insensitive regex search
        collection_email.update_many(query,{"$addToSet": {"jobtitle": job_title}})
     
