from src.db.repository import PostRepository


class PostService:
    def __init__(self, repository: PostRepository) -> None:
        self.repository = repository
