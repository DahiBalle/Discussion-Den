from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, PasswordField, StringField, TextAreaField
from wtforms.validators import Email, InputRequired, Length, Optional, URL


class RegisterForm(FlaskForm):
    username = StringField(
        "Username", validators=[InputRequired(), Length(min=3, max=32)]
    )
    email = EmailField("Email", validators=[InputRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=6, max=72)])


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(min=3, max=32)])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=6, max=72)])


class PostForm(FlaskForm):
    title = StringField("Title", validators=[InputRequired(), Length(min=3, max=200)])
    body = TextAreaField("Body", validators=[InputRequired(), Length(min=1, max=10000)])
    image_url = StringField("Image URL (optional)", validators=[Optional(), URL(), Length(max=500)])


class CommentForm(FlaskForm):
    body = TextAreaField("Comment", validators=[InputRequired(), Length(min=1, max=5000)])


class EditProfileForm(FlaskForm):
    avatar = StringField("Avatar URL", validators=[Optional(), URL(), Length(max=500)])
    bio = TextAreaField("Bio", validators=[Optional(), Length(max=2000)])


class EditPersonaForm(FlaskForm):
    name = StringField("Persona name", validators=[InputRequired(), Length(min=2, max=48)])
    avatar = StringField("Avatar URL", validators=[Optional(), URL(), Length(max=500)])
    banner = StringField("Banner URL", validators=[Optional(), URL(), Length(max=500)])
    bio = TextAreaField("Bio", validators=[Optional(), Length(max=2000)])
    is_public = BooleanField("Public persona")


class CommunityForm(FlaskForm):
    """
    Form for creating new communities.
    
    Safety: Follows existing form patterns with proper validation.
    """
    name = StringField(
        "Community Name", 
        validators=[
            InputRequired(), 
            Length(min=2, max=64, message="Community name must be 2-64 characters")
        ]
    )
    description = TextAreaField(
        "Description", 
        validators=[Optional(), Length(max=500, message="Description too long")]
    )
    rules = TextAreaField(
        "Community Rules", 
        validators=[Optional(), Length(max=1000, message="Rules too long")]
    )

