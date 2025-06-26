Backend

In folder `backend`
1. Install dependency
```
pip install -r requirements.txt
```
2. Start program 
```
uvicorn main:app --reload
```
3. (Sample request) In separate terminal run
```
curl -X POST "http://127.0.0.1:8000/chat" -H "Content-Type: application/json" -d '{"session_id": "test_session", "message": "There are 3 floors, 2 gardens and 1 toilet."}'
```