from telegram_movie_tracker.tasks.celeryconfig import app

@app.task
def test_task(data) -> str:
    print(data)
    return 'success'
