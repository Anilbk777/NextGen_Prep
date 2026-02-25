from typing import List
from datetime import date, timedelta, datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.presentation.schemas.analytics_schema import SubjectProgress, DailyPoint
from app.presentation.dependencies import get_db, get_current_user
from app.infrastructure.repositories.analytics_repo_impl import AnalyticsRepository

router = APIRouter(tags=["Analytics"])


@router.get("/analytics/progress", response_model=List[SubjectProgress])
def get_progress(
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """Return daily per-subject progress for the current user.

    Response: list of subjects each with a `series` array containing daily points
    {date, subject_id, accuracy, attempts}.
    """
    user_id = current_user.get("user_id")

    # Default date window: last 7 days including today
    end_dt = date.today()
    start_dt = end_dt - timedelta(days=6)

    # Ensure strings passed to repo are ISO dates
    start_iso = start_dt.isoformat()
    end_iso = end_dt.isoformat()

    repo = AnalyticsRepository(db)
    rows = repo.get_daily_subject_progress(
        user_id=user_id, start_date=start_iso, end_date=end_iso
    )

    # Build a map {(subject_key, date_str) -> data}; subject_key includes source to avoid id collisions
    row_map = {}
    subject_keys_in_rows = set()
    for r in rows:
        # repository now returns a composite `subject_key` like 'practice:3' or 'mock:4'
        key = (r.get("subject_key"), r.get("date"))
        row_map[key] = r
        if r.get("subject_key") is not None:
            subject_keys_in_rows.add(r.get("subject_key"))

    # Build date range (inclusive)
    total_days = (end_dt - start_dt).days + 1
    date_list = [(start_dt + timedelta(days=i)).isoformat() for i in range(total_days)]

    out = []
    # Build subject key -> name map from practice and mock-test subjects
    from app.infrastructure.db.models import MockTestSubject, PracticeSubject

    practice_subs = db.query(PracticeSubject).all()
    mock_subs = db.query(MockTestSubject).all()

    subj_name_map: dict = {}
    # map practice subjects using a source-prefixed key
    for s in practice_subs:
        subj_name_map[f"practice:{s.id}"] = s.name
    # map mock subjects using a source-prefixed key
    for s in mock_subs:
        subj_name_map[f"mock:{s.id}"] = s.name
    # map missing/unknown subject key to a friendly name
    subj_name_map.setdefault(None, "Unknown")

    # Invert to map subject_name -> set of subject_keys (to merge subjects with same name)
    name_to_ids: dict = {}
    for skey, name in subj_name_map.items():
        name_to_ids.setdefault(name, set()).add(skey)
    # Ensure we include any subject keys present in rows even if not in subj_name_map
    for skey in subject_keys_in_rows:
        name = subj_name_map.get(skey, "Unknown")
        name_to_ids.setdefault(name, set()).add(skey)

    # For each subject name, combine data across all its IDs per date
    for name, ids_set in name_to_ids.items():
        series = []
        for d in date_list:
            attempts_sum = 0
            correct_sum = 0.0
            for sid in ids_set:
                r = row_map.get((sid, d))
                if not r:
                    continue
                a = int(r.get("attempts", 0))
                attempts_sum += a
                # compute correct count from accuracy * attempts
                correct_sum += float(r.get("accuracy", 0.0)) * a

            if attempts_sum > 0:
                accuracy = correct_sum / attempts_sum
            else:
                accuracy = 0.0

            series.append(
                DailyPoint(date=d, accuracy=accuracy, attempts=int(attempts_sum))
            )

        out.append(SubjectProgress(subject_name=name, series=series))

    return out
