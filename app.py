import request
import json
import os
import re

import requests
from flask import Flask, request, make_response
from flask_cors import cross_origin
from pymongo import MongoClient
from requests.exceptions import HTTPError

from SendEmail.sendEmail import EmailSender
from config_reader import ConfigReader

app = Flask(__name__)

# geting and sending response to dialogflow
@app.route('/webhook', methods=['POST'])
@cross_origin()
def webhook():
    config_reader = ConfigReader()
    configuration = config_reader.read_config()

    client = MongoClient(
        "mongodb+srv://your_username:" + configuration["MONGO_PASSWORD"] + "@cluster0-p5lkb.mongodb.net/dialogflow?retryWrites=true&w=majority")

    db = client.dialogflow

    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    intent_check = req.get("queryResult").get("intent").get("displayName")

    if (intent_check == "AboutCorona" or
        intent_check == "CountryCases" or
        intent_check == "CovidMap" or
        intent_check == "CovidTest" or
        intent_check == "Fallback" or
        intent_check == "Goodbye" or
        intent_check == "Menu" or
        intent_check == "MyAreaCases" or
        intent_check == "MythBuster" or
        intent_check == "Precaution" or
        intent_check == "QuarantineTips" or
        intent_check == "StateCases" or
        intent_check == "Symptoms" or
        intent_check == "Welcome"):
        res = saveToDb(req, db)
    elif intent_check == "GetCountryName":
        res = getCountryName(req, db)
    elif intent_check == "GetStateName":
        res = getStateName(req, db)
    elif intent_check == "GetUserDetails":
        res = getUserDetails(req, db)
    elif intent_check == "GlobalCases":
        res = globalCases(req, db)
    elif intent_check == "IndiaCases":
        res = indiaCases(req, db)
    elif intent_check == "News":
        res = news(req, db)

    res = json.dumps(res, indent=4)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

def saveToDb(req, db):
    sessionID = req.get("session")
    session = re.compile("sessions/(.*)")
    sessionID = session.findall(sessionID)[0]
    result = req.get("queryResult")
    user_says = result.get("queryText")
    bot_says = result.get("fulfillmentText")
    if db.conversations.find({"sessionID": sessionID}).count() > 0:
        db.conversations.update_one({"sessionID": sessionID}, {
                                "$push": {"events": {"$each": [user_says, bot_says]}}})
    else:
        db.conversations.insert_one(
            {"sessionID": sessionID, "events": [user_says, bot_says]})
    print("Conversation Saved to Database!")


def globalCases(req, db):
    sessionID = req.get("session")
    session = re.compile("sessions/(.*)")
    sessionID = session.findall(sessionID)[0]
    result = req.get("queryResult")
    user_says = result.get("queryText")
    try:
        url = "https://api.covid19api.com/summary"
        res = requests.get(url)
        jsonRes = res.json()
        totalGlobalCases = jsonRes["Global"]
        confirmed = str(totalGlobalCases["TotalConfirmed"])
        recovered = str(totalGlobalCases["TotalRecovered"])
        deaths = str(totalGlobalCases["TotalDeaths"])
        fulfillmentText = "Confirmed Cases: " + confirmed + "\nRecovered Cases: " + recovered + "\nDeaths: " + deaths
        bot_says = fulfillmentText
        if db.conversations.find({"sessionID": sessionID}).count() > 0:
            db.conversations.update_one({"sessionID": sessionID}, {
                "$push": {"events": {"$each": [user_says, bot_says]}}})
        else:
            db.conversations.insert_one(
                {"sessionID": sessionID, "events": [user_says, bot_says]})
        return {
            "fulfillmentText": fulfillmentText
        }

    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")


def news(req, db):
    sessionID = req.get("session")
    session = re.compile("sessions/(.*)")
    sessionID = session.findall(sessionID)[0]
    result = req.get("queryResult")
    user_says = result.get("queryText")
    try:
        config_reader = ConfigReader()
        configuration = config_reader.read_config()
        url = "http://newsapi.org/v2/top-headlines?country=in&category=health&apiKey=" + \
            configuration['NEWS_API']
        res = requests.get(url)
        jsonRes = res.json()
        articles = jsonRes["articles"]
        news = list()
        for i in range(len(articles)):
            title = articles[i]["title"]
            author = articles[i]["author"]
            news_final = str(i + 1) + ". " + \
                str(title) + " - " + str(author)
            news.append(news_final)
        fulfillmentText = "\n".join(news)
        bot_says = fulfillmentText
        if db.conversations.find({"sessionID": sessionID}).count() > 0:
            db.conversations.update_one({"sessionID": sessionID}, {
                "$push": {"events": {"$each": [user_says, bot_says]}}})
        else:
            db.conversations.insert_one(
                {"sessionID": sessionID, "events": [user_says, bot_says]})
        return {
            "fulfillmentText": fulfillmentText
        }

    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")


if __name__ == '__main__':
    app.run(debug=False)
