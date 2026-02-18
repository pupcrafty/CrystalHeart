extends CanvasLayer

@export var refresh_interval: float = 0.1
@export var max_bands_to_show: int = 12

@onready var _audio_service: Node = get_node_or_null("../AudioServiceOSC")
@onready var _label: Label = $MarginContainer/DebugLabel

var _time_since_refresh: float = 0.0

func _ready() -> void:
	if _audio_service == null:
		_label.text = "Audio debug: AudioServiceOSC node not found"
		return
	_label.text = "Audio debug: waiting for /audio/bands_normalized..."

func _process(delta: float) -> void:
	if _audio_service == null:
		return
	_time_since_refresh += delta
	if _time_since_refresh < refresh_interval:
		return
	_time_since_refresh = 0.0
	_refresh_debug_text()

func _refresh_debug_text() -> void:
	if not _audio_service.has_method("get_normalized_bands"):
		_label.text = "Audio debug: AudioServiceOSC missing get_normalized_bands()"
		return

	var payload: Dictionary = _audio_service.get_normalized_bands("/audio/bands_normalized")
	if payload.is_empty():
		var bpm := 0.0
		if _audio_service.has_method("get_float"):
			bpm = _audio_service.get_float("/clock/bpm")
		_label.text = "Audio debug: no bands yet (bpm %.1f)" % bpm
		return

	var total: int = int(payload.get("total", 0))
	var active: int = int(payload.get("active", 0))
	var bands: Array = payload.get("bands", [])

	bands.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		return float(a.get("normalized", 0.0)) > float(b.get("normalized", 0.0))
	)

	var line_count: int = mini(max_bands_to_show, bands.size())
	var lines: PackedStringArray = []
	var beat_id: int = 0
	var bpm: float = 0.0
	if _audio_service.has_method("get_int"):
		beat_id = _audio_service.get_int("/clock/beat_id")
	if _audio_service.has_method("get_float"):
		bpm = _audio_service.get_float("/clock/bpm")

	lines.append("OSC /audio/bands_normalized")
	lines.append("bpm %.1f  beat %d  active %d/%d" % [bpm, beat_id, active, total])

	for i in range(line_count):
		var band: Dictionary = bands[i]
		lines.append(
			"#%03d  norm %.3f  ema %.3f" % [
				int(band.get("index", 0)),
				float(band.get("normalized", 0.0)),
				float(band.get("ema", 0.0))
			]
		)

	_label.text = "\n".join(lines)
