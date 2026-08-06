import os
import asyncio
import logging
from dotenv import load_dotenv

from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, llm
from livekit.plugins import openai, elevenlabs, silero

# Import your existing LangGraph logic
from graph.pipeline import run_gm_chat

load_dotenv()
logger = logging.getLogger("hotel-voice-agent")
logger.setLevel(logging.INFO)

class HotelCopilotAgent(Agent):
    def __init__(self) -> None:
        # Initialize the specific components from the DeepLearning.AI course
        vad = silero.VAD.load()
        stt = openai.STT(model="whisper-1")
        tts = elevenlabs.TTS()
        
        # Hijack OpenAI plugin to use Groq's LPU infrastructure for ultra-low latency
        groq_llm = openai.LLM(
            model="llama-3.1-8b-instant",
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ.get("GROQ_API_KEY")
        )

        super().__init__(
            instructions=(
                "You are the voice interface for a Hotel General Manager's AI Copilot. "
                "Keep your conversational responses extremely brief and professional. "
                "If the GM asks for data, metrics, or anomalies, immediately use the "
                "'query_hotel_systems' tool to get the accurate answer. Do not guess."
            ),
            stt=stt,
            llm=groq_llm,
            tts=tts,
            vad=vad,
        )

    # In LiveKit v1.0+, tools are attached directly to the Agent.
    # Note: Depending on your exact minor version, if it complains about function_tool, 
    # simply change it back to @llm.ai_callable.
    @llm.function_tool(
        description="Query the hotel intelligence system for revenue, operations, reputation, or payroll data."
    )
    async def query_hotel_systems(self, query: str) -> str:
        logger.info(f"🎤 Voice Agent triggered LangGraph with query: {query}")
        
        # We run this in a thread pool since your run_gm_chat is currently synchronous
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, run_gm_chat, query)
        
        return response


async def entrypoint(ctx: JobContext):
    """
    LiveKit entrypoint to initialize the WebRTC room and agent session.
    """
    await ctx.connect()

    session = AgentSession()
    
    agent = HotelCopilotAgent()
    
    await session.start(agent=agent, room=ctx.room)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
