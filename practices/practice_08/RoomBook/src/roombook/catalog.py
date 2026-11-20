from roombook.schemas import Room

ROOMS = (
    Room(id=101, name="Комната 101", capacity=4, equipment=("Маркерная доска",)),
    Room(id=102, name="Комната 102", capacity=8, equipment=("Маркерная доска", "Экран")),
    Room(id=103, name="Комната 103", capacity=12, equipment=("Маркерная доска", "Проектор")),
)
