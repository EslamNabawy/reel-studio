import builtins
import sys

sys.path.insert(0, ".")
import rag

questions = [
    "مين اعلى جي بي ايه",
    "اسكيلز حاجر",
    "كم عدد المتقدمين",
    "معدل نورهان كام",
    "exit",
]
it = iter(questions)
builtins.input = lambda *a, **k: next(it)
rag.main()
