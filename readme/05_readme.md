# MeetingGPT

<img src="images/Flow of MeetingGPT.png" width="400" />

<br>
<br>

## Description

A transcription generator for video calls. It provides the whole transcription of given video file and its summary, and returns replies for the questions about the content.

<br>

## The Structure of Chain

> - **Summary Tab : Map-Reduce prompt + LLM(gpt-3.5-turbo)** <br>
> - **Map-Reduce Chain** : first_summary_chain + refine_chain <br><br>
> - **QnA Tab : retriever(Vectorstore: FAISS) + Stuff prompt + LLM(gpt-3.5-turbo) + ConversationBufferMemory**

<br>

## Map-Reduce prompt

```
first_summary_prompt = ChatPromptTemplate.from_template(
                    """
                        Write a concise summary of the following:
                        "{text}"
                        CONCISE SUMMARY:
                    """
                )

refine_prompt = ChatPromptTemplate.from_template(
                """
                Your job is to produce a final summary.
                We have provided an existing summary up to a
                certain point: {existing_summary}
                We have the opportunity to refine the existing
                summary (only if needed) with some more context
                below.
                -------------
                {text}
                -------------
                Given the new context, refine the original
                summary.
                If the context isn't useful, RETURN the
                original summary.
                """
            )
```

<br>
<br>
<br>
