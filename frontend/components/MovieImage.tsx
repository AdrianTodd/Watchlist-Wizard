// frontend/components/MovieImage.tsx
"use client"; // <--- MARK THIS AS A CLIENT COMPONENT

import Image from "next/image"; // Use Next.js Image component for optimization
import { useState } from "react";

interface MovieImageProps {
  src: string | null;
  alt: string;
  width: number;
  height: number;
  className?: string;
  priority?: boolean;
}

const MovieImage: React.FC<MovieImageProps> = ({
  src,
  alt,
  width,
  height,
  className = "",
  priority = false,
}) => {
  const placeholderImg = "/placeholder-image.png";
  const [imgSrc, setImgSrc] = useState(src || placeholderImg);

  const handleError = () => {
    setImgSrc(placeholderImg);
  };

  return (
    <Image
      src={imgSrc}
      alt={alt}
      onError={handleError}
      className={className}
      loading={priority ? "eager" : "lazy"}
      priority={priority}
      width={width}
      height={height}
      style={{ objectFit: "cover" }} // Maintain aspect ratio using style
    />
  );
};

export default MovieImage;
