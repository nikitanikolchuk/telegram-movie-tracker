from telegram_movie_tracker.celeryconfig import app

@app.task
def test_task(data) -> str:
    print(data)
    return 'success'
