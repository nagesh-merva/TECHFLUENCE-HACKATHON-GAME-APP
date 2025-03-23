import os
from flask import Flask, render_template, request, jsonify, session
from pymongo import MongoClient
from datetime import datetime
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

uri = os.getenv("MONGO_URI")
client = MongoClient(uri)

db= client["hackathon"]

teams = db["teams"]
submissions = db["submissions"]
tokens =db["tokens"]
startTime = db["startTime"]


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-teams', methods=['GET'])
def get_teams():
    all_teams = list(teams.find({}, {"name": 1, "_id": 0}))
    team_names = [team["name"] for team in all_teams]
    return jsonify({"success": True, "teams": team_names})

@app.route('/submit-code', methods=['POST'])
def submit_code():
    team_name = request.form.get('team_name')
    entered_code = request.form.get('code')
    
    print(team_name , "- " , entered_code)
    
    session['team_name'] = team_name
    
    team = teams.find_one({"name": team_name})
    print(team)
    if not team:
        return jsonify({"success": False, "message": "Team not found"})
    
    if team["code"] == entered_code:
        return jsonify({"success": True,"matched_team": team['teamHtoken'], "message": f"Code verified! Find team {team['teamHtoken']} to get your token."})
    
    return jsonify({"success": False, "message": "Invalid code. Try again."}),400

@app.route('/submit-token', methods=['POST'])
def submit_token():
    token_code = request.form.get('token_code')
    team_name = session.get('team_name')
    
    if not team_name:
        return jsonify({"success": False, "message": "Session expired. Please start over."})
    
    team = teams.find_one({"name": team_name})
    team_type = team["type"]
    
    query = {"token_code": token_code}
    if team_type == "retro":
        query["retro_team"] = team_name
    else:
        query["future_team"] = team_name
    
    token_doc = tokens.find_one(query)
    
    if token_doc:
        existing_submission = submissions.find_one({"team_name": team_name})
        if existing_submission:
            return jsonify({"success": False, "message": "You've already completed the challenge!"})
        
        submission_time = datetime.now()
    
        start_time_doc = startTime.find_one({})
        if not start_time_doc or "start_time" not in start_time_doc:
            return jsonify({"success": False, "message": "Game has not started yet."})
        
        start_time = datetime.fromisoformat(start_time_doc["start_time"])
        
        print(start_time)
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        
        elapsed_minutes = (submission_time - start_time).total_seconds() / 60
        
        if elapsed_minutes <= 10:
            points = 25
        elif elapsed_minutes <= 20:
            points = 20
        else:
            points = 15
        
        submissions.insert_one({
            "team_name": team_name,
            "submission_time": submission_time,
            "points": points
        })
        
        return jsonify({
            "success": True,
            "message": f"Congratulations! You've completed the challenge and earned {points} points!",
            "points": points
        })
    
    return jsonify({"success": False, "message": "Invalid token. Try again."})

@app.route('/start-game', methods=['POST'])
def start_game():
    start_time = datetime.now().isoformat()
    startTime.update_one({}, {"$set": {"start_time": start_time}}, upsert=True)
    return jsonify({"success": True, "message": "Game started!", "start_time": start_time})

if __name__ == '__main__':
    app.run(debug=True)