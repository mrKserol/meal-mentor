type MealPhotoPreviewProps = {
  imageBase64?: string | null;
  imageUrl?: string | null;
};

export function MealPhotoPreview({ imageBase64, imageUrl }: MealPhotoPreviewProps) {
  const src = imageBase64
    ? `data:image/jpeg;base64,${imageBase64}`
    : imageUrl?.trim()
      ? imageUrl
      : null;

  if (!src) return null;

  return (
    <img
      src={src}
      alt="Фото блюда"
      className="max-h-64 w-full rounded-xl object-cover"
    />
  );
}
