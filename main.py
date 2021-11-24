from os import error
import streamlit as st
from streamlit.uploaded_file_manager import UploadedFile
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import ObjectId
from PIL import Image
import boto3
from botocore.exceptions import ClientError
import io

if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'login_response' not in st.session_state:
    st.session_state['login_response'] = None
if 'coupon_response' not in st.session_state:
    st.session_state['coupon_response'] = None
if 'new_user_coupons' not in st.session_state:
    st.session_state["new_user_coupons"] = []
if 'upload_state' not in st.session_state:
    st.session_state["upload_state"] = None
if 'user_wants_to_override' not in st.session_state:
    st.session_state["user_wants_to_override"] = False

mongo_url = st.secrets['MONGO_URL']
aws_access = st.secrets['AWS_ACCESS_KEY_ID']
aws_secret = st.secrets['AWS_SECRET_ACCESS_KEY']
all_entreprises = ['LE PISTON', 'AGC', 'ST MICROELECTRONICS', 'GPC', 'MASCIR', 'MAGHREB STEEL', 'YAZAKI', 'OCP',
                   'STELLANTIS', 'OCP MS', 'MECOMAR', 'ALTEN', "O'DASSIA", 'VALEO', 'JESA', 'DICASTAL', 'TE CONNECTIVITY', 'LEONI']
all_coupons = ['Q7PX', 'X1Z0', 'ZF51', 'Z0S9', '2WBK', 'S3QN', 'VUQB', 'ONLG', 'KZKI',
               'JD8D', 'J0AC', 'PO2M', 'KWS0', 'BHQ2', 'JLFF', 'LNNX', 'S0P6', '03AO', 'CV5N', 'EGDM']


@st.cache(hash_funcs={MongoClient: id, Database: id})
def get_db() -> Database:
    global mongo_url
    return MongoClient(mongo_url)['fame-cv']


def login():
    email = st.session_state['logging_form_email'].strip().lower()

    if not email.endswith("@edu.umi.ac.ma"):
        st.session_state['login_response'] = "WRONG_TYPE"
    else:
        db = get_db()
        users = db['users']
        user = users.find_one({'email': email})
        default_user = {
            '_id': ObjectId(),
            'email': email,
            'name': '',
            'resume_url': None,
            'coupons': [],
            'entreprises': []
        }
        if user is None:
            users.insert_one(default_user)
            user = users.find_one({'email': email})
        st.session_state["user"] = user
        st.session_state['selected_entreprises'] = user.get('entreprises')
        st.session_state['user_name'] = user.get('name')
        st.session_state['user_coupons'] = user.get('coupons')


def check_max(max_selections: int):
    if len(st.session_state['selected_entreprises']) > max_selections:
        st.session_state['selected_entreprises'] = st.session_state['selected_entreprises'][:max_selections]


def apply_code():
    global all_coupons
    code = st.session_state['coupon_code']

    if code not in all_coupons:
        st.session_state['coupon_response'] = 'WRONG'
    elif code in st.session_state['user_coupons'] or code in st.session_state["new_user_coupons"]:
        st.session_state['coupon_response'] = 'DUPE'
    else:
        st.session_state['coupon_response'] = 'ADDED'
        st.session_state['coupon_code'] = ''
        st.session_state["new_user_coupons"] = st.session_state["new_user_coupons"] + [code]


def save_codes():
    codes = st.session_state["new_user_coupons"].copy()
    st.session_state["new_user_coupons"] = []

    db = get_db()
    users = db['users']
    users.update_one({"_id": st.session_state["user"].get('_id')}, {
                     '$addToSet': {'coupons': {'$each': codes}}})

    user = users.find_one({"_id": st.session_state["user"].get('_id')})
    st.session_state["user"] = user
    st.session_state['selected_entreprises'] = user.get('entreprises')
    st.session_state['user_name'] = user.get('name')
    st.session_state['user_coupons'] = user.get('coupons')


def save_preferences():
    db = get_db()
    users = db['users']
    users.update_one({"_id": st.session_state["user"].get('_id')}, {
                     '$set': {'name': st.session_state['user_name'], 'entreprises': st.session_state['selected_entreprises']}})

    user = users.find_one({"_id": st.session_state["user"].get('_id')})
    st.session_state["user"] = user
    st.session_state['selected_entreprises'] = user.get('entreprises')
    st.session_state['user_name'] = user.get('name')
    st.session_state['user_coupons'] = user.get('coupons')


def upload_file(uploaded_file: UploadedFile, name: str = None):
    s3_client = boto3.client(
        's3', aws_access_key_id=aws_access, aws_secret_access_key=aws_secret)
    name = name if name is not None else uploaded_file.name
    try:
        uploaded_file.seek(0)
        file_object = io.BytesIO(uploaded_file.read())
        s3_client.upload_fileobj(
            file_object, 'fame-cv', name)
        return True
    except ClientError as e:
        print(e)
        return False


def save_cv():
    uid: ObjectId = st.session_state["user"].get('_id')
    uploaded_file: UploadedFile = st.session_state["uploaded_cv"]
    file_name: str = uploaded_file.name
    file_name = file_name.split(".")[-1]
    file_uploaded = upload_file(uploaded_file, "%s.%s" % (str(uid), file_name))
    if file_uploaded:
        st.session_state["upload_state"] = "OK"
        db = get_db()
        users = db['users']
        users.update_one({"_id": st.session_state["user"].get('_id')}, {
                        '$set': {'resume_url': "s3://fame-cv/%s.%s" % (str(uid), file_name)}})
        user = users.find_one({"_id": st.session_state["user"].get('_id')})
        st.session_state["user"] = user
        st.session_state['user_wants_to_override'] = False
    else:
        st.session_state["upload_state"] = "ERROR"

def override_cv():
    st.session_state['user_wants_to_override'] = True

logo = Image.open("xxx.png")

st.set_page_config(page_title="CV Platform", page_icon="🤖")
st.markdown(
    r"""
    <style>
        footer, header button { visibility: hidden }
        .main { background-color: white; }
    </style>
    """, unsafe_allow_html=True)

st.image(logo)
st.markdown("&nbsp;")

st.title("FAME CV Platform")

if st.session_state['user'] is None:
    st.header("Instructions")
    st.write("You can get started by typing your academic email (@edu.umi.ac.ma).")
    st.header("Authentication")
    with st.form("logging_form"):
        st.text_input("Email", key="logging_form_email")
        if st.session_state['login_response'] == "WRONG_TYPE":
            st.error("Please use your @edu.umi.ac.ma account.")
        st.form_submit_button("Next", on_click=login)

if st.session_state['user'] is not None:
    user = st.session_state['user']
    max_selections = 10 + len(user.get('coupons'))
    user_has_cv = user['resume_url'] is not None
    user_wants_to_override = st.session_state['user_wants_to_override']
    st.header("Profile")
    st.subheader("Preferences")

    st.text_input("Full Name", key="user_name")

    st.multiselect("Entreprises (max: %d)" % max_selections, all_entreprises,
                   key='selected_entreprises', on_change=check_max, args=(max_selections,))

    st.button("Save preferences", on_click=save_preferences)

    st.subheader("Upload CV")
    if user_has_cv and not user_wants_to_override:
        if st.session_state["upload_state"] is None:
            st.info('You have already uploaded a CV.')
            st.button("Upload a new CV", on_click=override_cv)
        elif st.session_state["upload_state"] == "ERROR":
            st.error("Error uploading the CV, please retry.")
        elif st.session_state["upload_state"] == "OK":
            st.success("CV updated successfully.")
        st.session_state["upload_state"] = None
    else:
        st.file_uploader("Resumé", type=['doc', 'docx', 'pdf'], key='uploaded_cv')
        if st.session_state["uploaded_cv"] is not None:
            st.button("Set as current CV", on_click=save_cv)
    st.markdown("&nbsp;")

    st.subheader("Unlock more selections")
    st.write(
        "If you want to unlock more selections, simply type below the codes from the conferences.")
    col1, col2 = st.columns([3, 1])
    new_coupons = st.session_state['new_user_coupons']
    st.text_input("Code", key="coupon_code")
    st.button("Add", on_click=apply_code)
    if st.session_state['coupon_response'] == 'ADDED':
        st.success('The code was successfully added.')
    elif st.session_state['coupon_response'] == 'DUPE':
        st.warning('You already added this code.')
    elif st.session_state['coupon_response'] == 'WRONG':
        st.error('This code does not exist.')
    if new_coupons:
        st.markdown("**New codes:**")
        st.markdown("\n".join(map(lambda code: " - %s" % code, new_coupons)))
        st.markdown(
            """Click "Save codes" to add the codes above to your account.""")
        st.button("Save codes", on_click=save_codes)

    st.session_state['coupon_response'] = None
