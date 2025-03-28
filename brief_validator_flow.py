"""
Mermaid diagram showing the brief validation flow.
"""

def draw_mermaid_png():
    mermaid_diagram = """
    graph TD
        A[Input Brief Text] --> B[LLM Extraction]
        B --> C{Extracted Info}
        
        C --> D[Validation Process]
        D --> E{Critical Info Check}
        D --> F{Non-Critical Info Check}
        D --> G{Format Validation}
        
        E --> H[Missing Critical]
        F --> I[Missing Non-Critical]
        G --> J[Validation Warnings]
        
        H --> K[Final Report]
        I --> K
        J --> K
        
        subgraph "Critical Fields"
            E1[Budget]
            E2[Languages]
            E3[Period]
            E4[Target Audience]
            E5[Campaign Target]
        end
        
        subgraph "Non-Critical Fields"
            F1[Client]
            F2[Brand]
            F3[Product]
            F4[Campaign]
            F5[Date]
            F6[Deadline]
            F7[Creative Agency]
            F8[Business Team]
        end
        
        subgraph "Validation Rules"
            G1[Budget Format]
            G2[Language Format]
            G3[Creative Agency Format]
            G4[Business Team Format]
        end
        
        E --> E1
        E --> E2
        E --> E3
        E --> E4
        E --> E5
        
        F --> F1
        F --> F2
        F --> F3
        F --> F4
        F --> F5
        F --> F6
        F --> F7
        F --> F8
        
        G --> G1
        G --> G2
        G --> G3
        G --> G4
    """
    
    # Save the diagram to a file
    with open("brief_validator_flow.mmd", "w") as f:
        f.write(mermaid_diagram)
    
    print("Mermaid diagram has been saved to 'brief_validator_flow.mmd'")
    print("You can now use this file with Mermaid CLI or an online Mermaid editor to generate the PNG")

if __name__ == "__main__":
    draw_mermaid_png() 