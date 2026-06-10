#!/bin/bash
# Extract SIMMOON API key from config.json → .env.voteapi
# Used by simmoon-voteapi.service ExecStartPre
API_KEY=$(python3 -c "import json; print(json.load(open('/home/docus/Simmoon_arc/config.json')).get('vote_api',{}).get('api_key',''))" 2>/dev/null)
echo "SIMMOON_API_KEY=$API_KEY" > /home/docus/Simmoon_arc/.env.voteapi
chmod 600 /home/docus/Simmoon_arc/.env.voteapi
