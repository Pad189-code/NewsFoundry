"use client";

import Image from "next/image";
import { ChatMarkdown } from "@/components/ChatMarkdown";
import type { MessageDTO } from "@/lib/api";

function formatMessageTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("fr-FR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

type ChatMessageBubbleProps = {
  message: MessageDTO;
};

export function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  const time = formatMessageTime(message.created_at);

  if (message.role === "user") {
    return (
      <div className="flex justify-end gap-2">
        <div className="max-w-[min(100%,28rem)]">
          <div className="rounded-md bg-[#23232f] p-4 text-sm text-white break-words whitespace-pre-wrap">
            {message.content}
          </div>
          {time ? (
            <p className="mt-1 text-right text-[10px] text-slate-400">{time}</p>
          ) : null}
        </div>
        <div
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-300 text-xs text-slate-600"
          aria-hidden
        >
          👤
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-2">
      <Image
        src="/Robo.png"
        alt=""
        width={32}
        height={32}
        className="h-8 w-8 shrink-0 rounded-full object-contain"
        aria-hidden
      />
      <div className="max-w-[min(100%,36rem)]">
        <div className="rounded-md bg-white p-4 text-sm text-slate-700 break-words shadow-sm">
          <ChatMarkdown content={message.content} />
        </div>
        {time ? (
          <p className="mt-1 text-[10px] text-slate-400">{time}</p>
        ) : null}
      </div>
    </div>
  );
}
