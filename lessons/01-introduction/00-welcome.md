# Welcome!

Welcome to the learning gem5 online bootcamp! We're excited to have you, and we hope you're excited to get started with gem5. This section will introduce you to how the bootcamp is organized.

> By the end of this section, you will be able to:  
>  
> - **Describe** how the learning gem5 bootcamp is organized.
> - **Explain** what learning objectives are.

## Learning objectives

You might've noticed the box in at the top labeled "By the end of this section, you will be able to". These are the section's *learning objectives*, and they'll be at at the top of every section. These are meant to help you recognize whether you met the section's goals. If, after going through a section, you can confidently say you can do what's in its learning objectives box, it's safe to say you're ready to move on.

## Assumed knowledge

This bootcamp makes some assumptions about what you already know in order to engage with the material. gem5 is a computer architecture simulator, meaning that computer architecture knowledge is expected and will not be covered in detail. We assume that you have taken the following university-level courses or acquired the equivalent knowledge elsewhere:

- Computer Organization
- Computer Architecture I and II

We also assume knowledge in the following areas:

- C++ and Python programming
- Programming tools such as Makefiles, GDB, and the command line
- Software such as Git/GitHub and VSCode

> Please refer to the [knowledge checklist](supp-knowledge-checklist.md) for a detailed list of assumed knowledge and resources if you need to fill in the gaps.

## Organization and tracks

This bootcamp is divided into units and sections.

> <details open>
>  <summary> <b>Bootcamp outline</b> </summary>
>
> ### Unit I: Introduction
>
> #### Section 1: Why simulation?
>
> #### Section 2: Enter gem5
>
> #### Section 3: Your first configuration script
>
> ### Unit II: Beginning gem5 simulation
>
> #### Section 1: Using the gem5 standard library
>
> #### Section 2: gem5 resources
>
> #### Section 3: Modeling processors in gem5
> 
> #### Section 4: Modeling classic caches in gem5
>
> #### Section 5: Modeling memory in gem5
>
> #### Section 6: **\[Project\]** Putting it all together
>
> ### Unit III: Intermediate gem5 features
>
> #### Section 1: Traffic generation
>
> #### Section 2: Simulation modes
>
> #### Section 3: Exit events
>
> #### Section 4: Communicating from guest to simulator
>
> ### Unit IV: Developing gem5 models
>
> #### **Track A: Processors**
>
> ##### Section 1: X
>
> #### **Track B: Caches**
>
> ##### Section 1: Y
>
> #### **Track C: Memory**
>
> ##### Section 1: Z
>
> ### Unit V: Advanced gem5 concepts
>
> #### Section 1: KVM fast-forwarding
>
> #### Section 2: Checkpointing
>
> #### Section 3: Sampled simulation
>
> #### Section 4: MultiSim
>
> #### Section 5: Creating disk images
>
> #### Section 6: Power modeling
>
> </details>

<!-- TODO (Naama): Finish the outline when everything is decided-->
\
You are encouraged to complete the units in order, but you can always jump around or skip sections if you're familiar with their subject matter. Use the learning objectives to guide you!

Unit IV is unique as it's split into 3 tracks: Processors, Caches, and Memory. **You may choose to complete any number of these tracks and still complete the bootcamp**. These tracks are independent and convey similar information about simulating in gem5, but their emphasis and encompassing project differ in focus. You can choose to complete all 3 tracks in a row, complete the entire bootcamp with one track then come back to the other tracks, or do one track and call it good. It depends on your goals and how you'll use gem5!

<!-- ## Knowledge checkpoints

 During some sections, you will see a knowledge checkpoint (KC) designed for you to self-test whether you understood the section's contents.  

The knowledge checkpoint question, and the answer options, will be visible. Come up with your answer, then expand the dropdown to reveal the correct answer and a short explanation. For example,  

> **(KC)** Are you excited to learn gem5?  
>
> - Yes
> - No  

> <details>
> <summary>Answer</summary>
> The correct answer is <b>yes</b>. gem5 is very exciting!
> </details>
\
Congrats on completing the first section! Let's get on with the contents of the bootcamp.
-->

## Acknowledgements  

This bootcamp is built upon previous in-person gem5 bootcamps:

- [gem5 Bootcamp UC Davis 2024](https://gem5bootcamp.github.io/2024/)
- [gem5 Bootcamp Latin America 2024](https://gem5bootcamp.github.io/latin-america-2024/)

Some sections are based on the gem5 tutorial and assignments for [CMPUT 429 at the University of Alberta](https://cmput429.github.io/429-website/). Thank you to Ayrton Chilibeck for contributing this resource.

The format of this bootcamp was inspired by [Learn You A Haskell For Great Good](https://learnyouahaskell.github.io/) by Miran Lipovača.
