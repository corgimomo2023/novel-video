from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    source_text: str = Field(default="", max_length=200_000)


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    source_text: str | None = Field(default=None, max_length=200_000)


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    voice: str = Field(default="zh-HK-HiuGaaiNeural", max_length=100)


class ShotCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(default="", max_length=4000)
    dialogue: str = Field(default="", max_length=4000)
    duration_seconds: float = Field(default=3.0, ge=1.0, le=20.0)
    engine: str = Field(default="wan_s2v", pattern="^(wan_s2v|echo_mimic|musetalk|camera_motion)$")
    reference_url: str | None = Field(default=None, pattern=r"^/api/media/uploads/[A-Za-z0-9._-]+$")
    audio_url: str | None = Field(default=None, pattern=r"^/api/media/uploads/[A-Za-z0-9._-]+$")


class ShotUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    prompt: str | None = Field(default=None, max_length=4000)
    dialogue: str | None = Field(default=None, max_length=4000)
    duration_seconds: float | None = Field(default=None, ge=1.0, le=20.0)
    engine: str | None = Field(default=None, pattern="^(wan_s2v|echo_mimic|musetalk|camera_motion)$")
    reference_url: str | None = Field(default=None, pattern=r"^/api/media/uploads/[A-Za-z0-9._-]+$")
    audio_url: str | None = Field(default=None, pattern=r"^/api/media/uploads/[A-Za-z0-9._-]+$")
