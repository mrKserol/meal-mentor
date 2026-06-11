import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MessageMarkdownProps {
  content: string;
}

export default function MessageMarkdown({ content }: MessageMarkdownProps) {
  return (
    <div className="max-w-none text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h3 className="mb-1 mt-2 text-base font-semibold">{children}</h3>,
          h2: ({ children }) => <h3 className="mb-1 mt-2 text-base font-semibold">{children}</h3>,
          h3: ({ children }) => <h3 className="mb-1 mt-2 text-sm font-semibold">{children}</h3>,
          p: ({ children }) => <p className="my-2 leading-relaxed">{children}</p>,
          ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
