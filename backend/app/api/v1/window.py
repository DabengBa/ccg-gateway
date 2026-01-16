from fastapi import APIRouter

router = APIRouter()

_show_callback = None


def set_show_callback(callback):
    global _show_callback
    _show_callback = callback


@router.post("/show")
async def show_window():
    if _show_callback:
        _show_callback()
        return {"success": True}
    return {"success": False, "message": "Not in desktop mode"}
