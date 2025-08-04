# Plan for Demo Paper
## Implementation tasks
- [] Refactor simulation folder
    - [] pm in pm package (low prio)

- [] refactor formatgenerator.py
    - [] extract simulation logic into simulation 
    - [] enable deliveries from different orders (high prio)

- [] add GUI (high prio)
    - [] interface for simulation results
    - [] interface for simulation inputs
    - [] configurable KPIs
    - [] interface for process mining inputs
    - [] interface for process mining results

- [] build standard process mining functions backend
- [] build integrable interface standards for new methods/KPIs
- [] other supply chain simulation related features?
- [] create new github for this

- more KPIs, like weighted average

## Talk with Mirjam
- sim: good
    - interesting approach to order splits - not captured in literature
- idea: job scheduling - depending on objective different ordering
- KPIs difficult: weighted average more promising
### Splits as productive measure
- how to optimize splitting/ what rules to apply? what alternative fixes
    - find split strategies
- productive adaptation with split policies, when to split?
- derive rule of thumbs
- how to implement splits as counter measure to delays/shortages?
    - how arbitrary can we make the splits

## Paper Requirements:
- the significance of the tool to the PM field;
- The innovations of the tool to the PM community and its main features;
- The maturity of the tool. For this section, one could provide a brief description of case studies performed using the tool, provide scalability data or pointers indicating where readers can find more information about these case studies;
- A link to a Web page where to download or use the tool. If the tool requires a license, a paper’s appendix should describe how to obtain a (temporary) license. The procedure to obtain the license must not disclose the identity of the reviewers. The appendix will not be included in the final version for the proceedings, if the demo is accepted;
- A link to a video that screencasts and demonstrates the tool, preferably including voice, which must not be longer than 4 minutes;

## Paper outline
- motivation: important intersection between pm and supply chain. Simulation relevant in both communities. Important to have close to natural data and suitable tools.
- context & related work 
- describe functionality and implementation





