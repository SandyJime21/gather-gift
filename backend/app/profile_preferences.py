"""Gift guide fields and completion for parent-managed profiles."""
def filled(value):
    if isinstance(value, dict):
        return any(filled(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(filled(v) for v in value)
    return bool(str(value).strip()) if value is not None else False


def completion(profile):
    interests = (profile.interests or []) + (profile.favorite_characters or []) + (profile.hobbies or []) + (profile.favorite_snacks or [])
    avatar = getattr(profile, 'avatar_key', None)
    picture = profile.photo_path or (avatar if avatar not in (None, '', 'flower', 'paw') else None)
    fields = [("Photo", picture), ("Birthday", profile.birthday), ("Allergies or none known", profile.allergies), ("Current favorites", interests)]
    if profile.profile_type == "pet":
        fields += [("Favorite treats or toys", profile.gift_preferences)]
    else:
        fields += [("Clothing size", profile.clothing_sizes), ("Shoe size", profile.shoe_sizes), ("Favorite colors", profile.favorite_colors)]
        if profile.is_adult:
            fields += [("Favorite brands", profile.favorite_brands), ("Favorite stores", profile.favorite_stores), ("Gift preferences", profile.gift_preferences)]
    missing = [label for label, value in fields if not filled(value)]
    total = len(fields)
    return {"percent": round((total-len(missing))*100/total), "missing": missing, "completed": total-len(missing), "total": total}


def gift_guide(profile):
    return {"profile_type": profile.profile_type, **{key: getattr(profile, key) for key in (
        "favorite_colors", "favorite_brands", "favorite_stores", "favorite_snacks", "favorite_characters", "interests", "hobbies", "clothing_sizes", "shoe_sizes", "gift_preferences", "allergies"
    )}}
