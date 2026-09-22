import type { ReactNode } from "react";

// Minimal, SAFE markdown renderer. Model output and documents are untrusted,
// so this never touches dangerouslySetInnerHTML — everything becomes React
// elements/text. Supports: # / ## / ### headings, **bold**, `inline code`,
// ``` fenced blocks, "- " bullet lists, paragraphs, and links (markdown
// [text](url) or bare URLs) restricted to http/https. Anything else is left
// as plain text.

const INLINE_RE =
  /(\*\*[^*]+\*\*)|(`[^`]+`)|(\[[^\]]+\]\(https?:\/\/[^\s)]+\))|(https?:\/\/[^\s]+)/g;

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let i = 0;
  INLINE_RE.lastIndex = 0;
  while ((match = INLINE_RE.exec(text)) !== null) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index));
    const token = match[0];
    const key = `${keyPrefix}-${i++}`;
    if (match[1]) {
      nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    } else if (match[2]) {
      nodes.push(<code key={key}>{token.slice(1, -1)}</code>);
    } else if (match[3]) {
      const linkMatch = /^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/.exec(token);
      if (linkMatch) {
        nodes.push(
          <a key={key} href={linkMatch[2]} target="_blank" rel="noopener noreferrer">
            {linkMatch[1]}
          </a>,
        );
      } else {
        nodes.push(token);
      }
    } else if (match[4]) {
      nodes.push(
        <a key={key} href={token} target="_blank" rel="noopener noreferrer">
          {token}
        </a>,
      );
    }
    lastIndex = match.index + token.length;
  }
  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}

export function Markdown({ text }: { text: string }) {
  const lines = text.split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  let blockKey = 0;
  let paragraphLines: string[] = [];
  let listItems: string[] = [];

  const flushParagraph = () => {
    if (paragraphLines.length) {
      const key = `p-${blockKey++}`;
      blocks.push(<p key={key}>{renderInline(paragraphLines.join(" "), key)}</p>);
      paragraphLines = [];
    }
  };
  const flushList = () => {
    if (listItems.length) {
      const key = `ul-${blockKey++}`;
      blocks.push(
        <ul key={key}>
          {listItems.map((item, idx) => (
            <li key={idx}>{renderInline(item, `${key}-${idx}`)}</li>
          ))}
        </ul>,
      );
      listItems = [];
    }
  };

  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith("```")) {
      flushParagraph();
      flushList();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++;
      blocks.push(
        <pre key={`code-${blockKey++}`}>
          <code>{codeLines.join("\n")}</code>
        </pre>,
      );
      continue;
    }
    const heading = /^(#{1,3})\s+(.*)$/.exec(line);
    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length;
      const key = `h-${blockKey++}`;
      const content = renderInline(heading[2], key);
      if (level === 1) blocks.push(<h1 key={key}>{content}</h1>);
      else if (level === 2) blocks.push(<h2 key={key}>{content}</h2>);
      else blocks.push(<h3 key={key}>{content}</h3>);
      i++;
      continue;
    }
    if (line.startsWith("- ")) {
      flushParagraph();
      listItems.push(line.slice(2));
      i++;
      continue;
    }
    if (line.trim() === "") {
      flushParagraph();
      flushList();
      i++;
      continue;
    }
    flushList();
    paragraphLines.push(line);
    i++;
  }
  flushParagraph();
  flushList();

  return <>{blocks}</>;
}
