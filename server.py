from flask import Flask, request, render_template
from twilio.twiml.messaging_response import MessagingResponse
from flask_sqlalchemy import SQLAlchemy
import os
import requests    # ← new import\
import restaurants
import time

# 📁 server.py -----

import json
from os import environ as env
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")

oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration'
) 


# auth0 routes 

@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )


@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )

# create db for tasks  
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///info.db'
dbt = SQLAlchemy(app)

	# db model 
class Info(dbt.Model):
    id = dbt.Column(dbt.Integer, primary_key=True)
    title = dbt.Column(dbt.String(100), nullable=False)
    content = dbt.Column(dbt.Text, nullable=False)

    def __repr__(self):
            return f"Post('{self.title}', '{self.content}')"
dbt.create_all(app=app)


@app.route("/")
def home():
    return render_template("index.html", session=session.get('user'), pretty=json.dumps(session.get('user'), indent=4))


@app.route("/about", methods=["GET", "POST"])
def about():
        return render_template("about.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard(): 
        return render_template("dashboard.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
        return render_template("contact.html")

@app.route("/sms", methods=['POST'])
def sms_reply():
    """Respond to incoming calls with a simple text message."""
    # Fetch the message
    msg = request.form.get('Body').lower()
    media_url = request.form.get('NumMedia')   
    tasks_content = dbt.session.query(Info.content).all()
    tasks_title = dbt.session.query(Info.title).all()

    # Create reply
    resp = MessagingResponse()

    if 'hi'.lower() in msg:
        resp.message(f"Hi there! I am Munchie your personal food bot. \n Here is the list of all commands\n 1)Type in set my budget - To set your current budget \n 2) restrictions: [your dietary restrictions] - to add your dietary restrictions \n 3) prefers: [cuisine] - to add your favourite cuisine \n 4) Send your current location so Munchie can find restaurants near you")
    
    elif 'Set my budget as'.lower() in msg:
            budget = msg.split(' ')[4]
            new_budget = Info(title='Budget', content=budget )
            dbt.session.add(new_budget)
            dbt.session.commit()
            resp.message(f"Your budget has been set as *{budget}*")

    elif 'restaurants near me'.lower() in msg:
            message = persistent_action=['geo:37.787890,-122.391664|375 Beale St']
            resp.message(restaurants.restaurants )

    elif 'chinese'.lower()  in msg: 
            prefers = msg.split(':')[5]
            new_prefers = Info(titles='Preferred cuisine', content=prefers)
            dbt.session.add(new_prefers)
            dbt.session.commit()
            resp.message(f"Delish! Your current cuisine preference has been set as {prefers}, feel free change it based on your preferences")

    elif 'restrictions:'.lower() in msg: 
            dietary_restrics = msg.split(':')[1] 
            new_diet = Info(title='dietary restrictions', content=dietary_restrics)
            dbt.session.add(new_diet)
            dbt.session.commit()
            resp.message(f"Great! Your dietary needs are set, feel free to change or add more dietary restrictions")


    else:
        lat , lon = request.form.get('Latitude'), request.form.get('Longitude') 
        resp.message(f"Your current location has been updated!!")



        
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)