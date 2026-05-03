type Props = {
  value: string;
  length?: number;
  className?: string;
};

export function Hash({ value, length = 12, className = "" }: Props) {
  if (!value) return null;
  return (
    <span className={`font-mono text-xs text-muted ${className}`}>
      {value.slice(0, length)}
      {value.length > length && "…"}
    </span>
  );
}
