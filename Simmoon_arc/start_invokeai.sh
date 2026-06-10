#!/bin/bash
# Start InvokeAI web UI persistently in WSL2
source ~/invokeai-env/bin/activate
invokeai-web --root ~/invokeai &
disown
sleep 2
echo "InvokeAI started. Check with: curl http://127.0.0.1:9090/api/v1/app/version"
