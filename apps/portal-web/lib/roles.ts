import type { Role } from "./types";

export interface RoleConfig {
  title: string;
  persona: string;
  accent: string;
  greeting: (name: string) => string;
  suggestions: string[];
}

export const ROLE_CONFIG: Record<Role, RoleConfig> = {
  student: {
    title: "Student Portal",
    persona: "Academic Assistant",
    accent: "#4f7cff",
    greeting: (name) => `Hi ${name.split(" ")[0]}! I'm EIS AI. Ask me about your attendance, or anything else about school.`,
    suggestions: ["What is my attendance?", "Was I marked absent last Monday?", "I'd like to talk to my teacher"],
  },
  parent: {
    title: "Parent Portal",
    persona: "Parent Support Assistant",
    accent: "#00a389",
    greeting: (name) => `Hello ${name.split(" ")[0]}, I'm EIS AI. I can help with your child's attendance and connect you with the school.`,
    suggestions: ["How much attendance does my child have?", "What about yesterday?", "I'm not satisfied — I want to talk to the teacher"],
  },
  teacher: {
    title: "Teacher Portal",
    persona: "Teaching Assistant",
    accent: "#7a5cf0",
    greeting: (name) => `Hello ${name}. I can pull up your class attendance or record it for you.`,
    suggestions: ["Mark Rahul absent today.", "Who is in my class?", "What is Priya's attendance?"],
  },
  principal: {
    title: "Management Portal",
    persona: "Management Assistant",
    accent: "#c2683a",
    greeting: (name) => `Good day, ${name}. I have school-wide attendance analytics ready when you are.`,
    suggestions: ["What is the overall attendance?", "Which class is lowest?", "How many students are below 75%?"],
  },
};
