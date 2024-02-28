import asyncio
import logging

from bench.runner import Runner, argstokwargs, parser


class ClosedBookRunner(Runner):
    def get_prompt(self, question, *args, **kwargs) -> str:
        question = question["question"]
        prompt = (
            "Answer the following question, and output only your answer. If the answer is a list, output one on"
            f" each line. Current date: 11-20-2023.\n\n[Question]: {question}"
        )
        return prompt


async def main():
    args = parser.parse_args()
    runner = ClosedBookRunner(bench_setting="closedbook", **argstokwargs(args))
    runner.load()
    await runner.run()
    await runner.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
