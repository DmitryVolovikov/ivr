import styles from "./LoadingSkeleton.module.css";

type LoadingSkeletonProps = {
  lines?: number;
};

export default function LoadingSkeleton({ lines = 3 }: LoadingSkeletonProps) {
  return (
    <div className={styles.skeleton}>
      {Array.from({ length: lines }).map((_, index) => (
        <span key={index} className={styles.line} />
      ))}
    </div>
  );
}
