"""
message_chains - Detect long method call chains (Law of Demeter violations).

Message chains occur when a client asks one object for another object,
then asks that object for yet another object, etc. (a.getB().getC().getD())
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("message_chains", category="code_smell", severity="medium")
@param("min_chain_length", int, default=3, description="Minimum chain length to report")
@param("limit", int, default=100, description="Maximum results to return")
def message_chains() -> Pipeline:
    """
    Detect message chains - long sequences of method calls.

    Returns:
        findings: List of message chains with locations
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?caller ?caller_name ?file ?line ?chain_length ?chain_text
            WHERE {
                ?chain type {MethodChain} .
                ?chain length ?chain_length .
                ?chain text ?chain_text .
                ?chain inMethod ?caller .
                ?caller name ?caller_name .
                ?chain inFile ?file .
                ?chain atLine ?line .
                FILTER ( ?chain_length >= {min_chain_length} )
            }
            ORDER BY DESC(?chain_length)
            LIMIT {limit}
        ''')
        .select("caller_name", "file", "line", "chain_length", "chain_text")
        .map(lambda r: {
            **r,
            "issue": "message_chain",
            "message": f"Method chain of length {r['chain_length']} in '{r['caller_name']}': {r.get('chain_text', '')}",
            "suggestion": "Apply 'Hide Delegate' or extract intermediate variables to reduce coupling"
        })
        .emit("findings")
    )
