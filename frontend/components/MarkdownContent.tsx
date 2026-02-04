import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownContentProps {
  content: string;
  className?: string;
}

/**
 * MarkdownContent Component
 * Renders markdown content with custom styled elements for agent responses.
 */
export const MarkdownContent: React.FC<MarkdownContentProps> = ({
  content,
  className = '',
}) => {
  if (!content) return null;

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      className={`markdown-content ${className}`}
      components={{
        // H2 headers - main sections
        h2: ({ children }) => (
          <h2 className="text-base font-bold text-slate-800 mt-4 mb-2 first:mt-0 pb-1 border-b border-slate-200">
            {children}
          </h2>
        ),
        // H3 headers - subsections
        h3: ({ children }) => (
          <h3 className="text-sm font-semibold text-slate-700 mt-3 mb-1.5 first:mt-0">
            {children}
          </h3>
        ),
        // H4 headers - minor sections
        h4: ({ children }) => (
          <h4 className="text-sm font-medium text-slate-600 mt-2 mb-1 first:mt-0">
            {children}
          </h4>
        ),
        // Paragraphs
        p: ({ children }) => (
          <p className="text-sm text-slate-700 leading-relaxed mb-2 last:mb-0">
            {children}
          </p>
        ),
        // Unordered lists
        ul: ({ children }) => (
          <ul className="space-y-1 text-sm text-slate-700 my-2 ml-1">
            {children}
          </ul>
        ),
        // Ordered lists
        ol: ({ children }) => (
          <ol className="space-y-1 text-sm text-slate-700 my-2 ml-1 list-decimal list-inside">
            {children}
          </ol>
        ),
        // List items
        li: ({ children }) => (
          <li className="flex items-start gap-2">
            <span className="text-slate-400 mt-0.5 flex-shrink-0">•</span>
            <span className="flex-1">{children}</span>
          </li>
        ),
        // Bold text
        strong: ({ children }) => (
          <strong className="font-semibold text-slate-800">{children}</strong>
        ),
        // Italic/emphasis
        em: ({ children }) => (
          <em className="italic text-slate-600">{children}</em>
        ),
        // Code inline
        code: ({ children }) => (
          <code className="px-1.5 py-0.5 bg-slate-100 rounded text-xs font-mono text-slate-700">
            {children}
          </code>
        ),
        // Code blocks
        pre: ({ children }) => (
          <pre className="p-3 bg-slate-50 rounded-lg overflow-x-auto text-xs font-mono my-2 border border-slate-200">
            {children}
          </pre>
        ),
        // Tables
        table: ({ children }) => (
          <div className="overflow-x-auto my-3">
            <table className="w-full text-xs border-collapse border border-slate-200 rounded-lg">
              {children}
            </table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-slate-50">{children}</thead>
        ),
        tbody: ({ children }) => <tbody>{children}</tbody>,
        tr: ({ children }) => (
          <tr className="border-b border-slate-200 last:border-b-0">
            {children}
          </tr>
        ),
        th: ({ children }) => (
          <th className="border border-slate-200 px-3 py-2 text-left font-semibold text-slate-700 bg-slate-50">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="border border-slate-200 px-3 py-2 text-slate-600">
            {children}
          </td>
        ),
        // Blockquotes
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-slate-300 pl-3 my-2 text-slate-600 italic">
            {children}
          </blockquote>
        ),
        // Horizontal rules
        hr: () => <hr className="my-3 border-slate-200" />,
        // Links
        a: ({ href, children }) => (
          <a
            href={href}
            className="text-blue-600 hover:text-blue-800 underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            {children}
          </a>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
};

export default MarkdownContent;
