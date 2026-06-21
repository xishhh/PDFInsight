from fastapi import HTTPException, status


def validate_question(question: str) -> str:
    stripped = question.strip()
    if not stripped:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty",
        )
    if len(stripped) <= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question must be longer than 3 characters",
        )
    return stripped
