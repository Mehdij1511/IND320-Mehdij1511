import streamlit as st
import pandas as pd
from pymongo import MongoClient


def connect_mongodb() -> MongoClient:
	"""Connect to MongoDB Atlas using the local or deployed secret."""
	try:
		uri = st.secrets["MONGODB_URI"]
	except KeyError as error:
		raise RuntimeError(
			"MONGODB_URI is missing from Streamlit secrets."
		) from error

	if not uri or uri.startswith("mongodb+srv://..."):
		raise RuntimeError("MONGODB_URI must contain a valid MongoDB URI.")

	client = MongoClient(uri, serverSelectionTimeoutMS=10000)
	client.admin.command("ping")
	return client


def load_monthly_flows() -> pd.DataFrame:
	"""Load processed monthly electricity-flow documents from MongoDB."""
	client = connect_mongodb()
	try:
		documents = list(
			client["ind320"]["monthly_electricity_flows"].find(
				{},
				{"_id": 0},
			)
		)
	finally:
		client.close()

	if not documents:
		raise RuntimeError("MongoDB contains no processed electricity-flow documents.")

	return pd.DataFrame(documents)
