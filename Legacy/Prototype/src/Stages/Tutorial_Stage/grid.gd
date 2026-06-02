extends TileMapLayer

@onready var grid := $TileMapLayer_Floor

func grid_to_world(cell: Vector2i) -> Vector2:
	return grid.map_to_local(cell)

func world_to_grid(pos: Vector2) -> Vector2i:
	return grid.local_to_map(pos)
