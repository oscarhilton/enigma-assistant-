import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Button } from "./button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from "./dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./dropdown-menu";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "./sheet";
import { Skeleton } from "./skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./tabs";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./tooltip";

describe("shadcn ui primitives", () => {
  it("renders Button, Skeleton, Tabs, Dialog, Sheet, Tooltip, DropdownMenu", () => {
    render(
      <TooltipProvider>
        <div>
          <Button>Click</Button>
          <Skeleton className="h-4 w-12" />
          <Tabs defaultValue="a">
            <TabsList>
              <TabsTrigger value="a">A</TabsTrigger>
            </TabsList>
            <TabsContent value="a">Tab A</TabsContent>
          </Tabs>
          <Dialog>
            <DialogTrigger>Open dialog</DialogTrigger>
            <DialogContent>
              <DialogTitle>Title</DialogTitle>
              <DialogDescription>Body</DialogDescription>
            </DialogContent>
          </Dialog>
          <Sheet>
            <SheetTrigger>Open sheet</SheetTrigger>
            <SheetContent>
              <SheetTitle>Sheet</SheetTitle>
            </SheetContent>
          </Sheet>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost">Tip</Button>
            </TooltipTrigger>
            <TooltipContent>Hint</TooltipContent>
          </Tooltip>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">Menu</Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem>Item</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </TooltipProvider>,
    );

    expect(screen.getByRole("button", { name: "Click" })).toBeInTheDocument();
    expect(screen.getByTestId("v2-skeleton")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "A" })).toBeInTheDocument();
    expect(screen.getByText("Tab A")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open dialog" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open sheet" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tip" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Menu" })).toBeInTheDocument();
  });
});
